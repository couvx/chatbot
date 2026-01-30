import streamlit as st
import json
import os
import pandas as pd
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from thefuzz import fuzz
from datetime import datetime

# --- 1. KONFIGURASI HALAMAN & TEMA ---
st.set_page_config(page_title="Klasifikasi Surat KPU", page_icon="📑", layout="centered")

# Custom CSS untuk replikasi UI Landing Page sesuai Gambar
st.markdown("""
    <style>
    /* Paksa Tema Terang */
    .stApp { background-color: white; color: #1e293b; }
    
    /* Area Header Atas */
    .header-container {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 0;
        border-bottom: 1px solid #f1f5f9;
        margin-bottom: 50px;
    }
    .header-logo {
        background-color: #e11d48;
        color: white;
        padding: 8px;
        border-radius: 8px;
        font-weight: bold;
    }
    .header-text h1 {
        font-size: 1.1rem !important;
        margin: 0 !important;
        color: #0f172a;
    }
    .header-text p {
        font-size: 0.75rem;
        margin: 0;
        color: #64748b;
    }

    /* Area Tengah (Landing) */
    .landing-container {
        text-align: center;
        margin-top: 100px;
        margin-bottom: 50px;
    }
    .landing-icon {
        background-color: #fff1f2;
        color: #e11d48;
        width: 80px;
        height: 80px;
        line-height: 80px;
        border-radius: 50%;
        font-size: 40px;
        margin: 0 auto 24px auto;
    }
    .landing-container h2 {
        font-size: 1.8rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 16px;
    }
    .landing-container p {
        color: #64748b;
        max-width: 500px;
        margin: 0 auto;
        line-height: 1.6;
    }
            
    /* --- BUBBLE USER (KANAN) --- */
    /* Mengatur kontainer agar pesan merapat ke kanan */
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
        flex-direction: row-reverse;
        background-color: transparent !important;
        transition: all 0.3s;
    }

    /* Mengatur bubble agar lebarnya menyesuaikan teks (fit-content) */
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] {
        background-color: #2C2C2E !important; /* Warna Merah */
        color: white !important; /* Warna Kuning */
        border-radius: 20px 5px 20px 20px !important;
        padding: 10px 16px !important;
        width: fit-content !important; /* Kunci agar bubble menyesuaikan teks */
        margin-left: auto; /* Memaksa bubble ke kanan */
    }

    /* --- STYLE BUBBLE ASSISTANT (KIRI) --- */
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
        background-color: transparent !important;
    }

    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) .st-emotion-cache-10t9u47,
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) [data-testid="stChatMessageContent"] {
        background-color: #f1f5f9 !important; /* Abu-abu sangat muda */
        color: #1e293b !important; /* Teks Gelap */
        border-radius: 5px 20px 20px 20px !important;
        padding: 12px 18px !important;
        border: 1px solid #e2e8f0;
    }

    [data-testid="stChatMessageAvatarAssistant"] {
        background-color: #64748b !important; /* Warna avatar asisten */
    }

    /* Perbaikan Jarak */
    [data-testid="stChatMessage"] {
        gap: 10px;
        padding: 1rem 0 !important;
    }

    /* Footer di bawah Input */
    .input-footer {
        font-size: 0.7rem;
        color: #94a3b8;
        text-align: center;
        margin-top: 10px;
    }

    /* Sidebar Styling (Tetap seperti instruksi sebelumnya) */
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-right: 1px solid #e0e0e0; }
    .sidebar-label { font-size: 0.75rem; font-weight: 800; color: #94a3b8; letter-spacing: 0.1rem; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. CORE FUNCTIONS ---

@st.cache_resource
def init_nlp():
    return StemmerFactory().create_stemmer()

@st.cache_data
def load_db():
    kode_data, jenis_data = [], []
    try:
        if os.path.exists('db_kode.json'):
            with open('db_kode.json', 'r', encoding='utf-8') as f:
                kode_data = json.load(f)
        if os.path.exists('db_jenis.json'):
            with open('db_jenis.json', 'r', encoding='utf-8') as f:
                jenis_data = json.load(f)
        return kode_data, jenis_data
    except Exception as e:
        st.error(f"Gagal memuat database: {e}")
        return [], []

def suggest_correction(query, db):
    words_pool = set()
    for item in db:
        content = f"{item.get('klasifikasi', '')} {item.get('keterangan', '')}".lower()
        words_pool.update("".join([c for c in content if c.isalnum() or c.isspace()]).split())
    
    best_match, highest_ratio = None, 0
    for word in words_pool:
        if len(word) < 4: continue
        ratio = fuzz.ratio(query.lower(), word)
        if ratio > highest_ratio:
            highest_ratio, best_match = ratio, word
            
    return best_match if 75 < highest_ratio < 100 else None

def smart_search(query, db, stemmer):
    if not db: return []
    query_clean = query.lower().strip()
    query_stemmed = stemmer.stem(query_clean)
    scored_results = []
    
    for item in db:
        klasifikasi = item.get('klasifikasi', '').lower()
        keterangan = item.get('keterangan', '').lower()
        kode = item.get('kode', '').lower()
        
        score = 0
        if query_clean == kode: score += 100
        elif query_clean in kode: score += 60
        
        text_score = fuzz.token_set_ratio(query_clean, f"{klasifikasi} {keterangan}")
        stem_bonus = 15 if query_stemmed in (klasifikasi + keterangan) else 0
        
        final_score = min(score + text_score + stem_bonus, 100)
        if final_score > 65:
            item_copy = item.copy()
            item_copy['score'] = final_score
            scored_results.append(item_copy)
            
    return sorted(scored_results, key=lambda x: x['score'], reverse=True)

# --- 3. INITIALIZATION ---
stemmer = init_nlp()
db_kode, db_jenis = load_db()

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Halo! Silakan tanya tentang **Kode Klasifikasi** atau **Jenis Surat**."}]

# --- 4. UI RENDERER ---
def render_results(results, title):
    if results:
        st.subheader(title)
        for r in results[:3]: # Limit 3 per kategori agar tidak terlalu panjang
            s = r.get('score', 0)
            clr = "green" if s > 85 else "orange"
            with st.expander(f"📍 {r.get('kode', 'N/A')} - {r.get('klasifikasi', 'Detail')}"):
                st.markdown(f":{clr}[**Relevansi: {s}%**]")
                st.write(f"**Sifat:** {r.get('sifat', '-')}")
                st.info(f"**Keterangan:** {r.get('keterangan', '-')}")
        st.divider()

# --- 4. SIDEBAR (SESUAI INSTRUKSI SEBELUMNYA) ---
with st.sidebar:
    st.markdown('<div class="sidebar-label">PERCAKAPAN</div>', unsafe_allow_html=True)
    st.button("💬 Chat Aktif", use_container_width=True, type="secondary")
    
    st.markdown("<div style='height: 65vh'></div>", unsafe_allow_html=True)
    st.divider()
    
    if st.session_state.messages:
        chat_data = pd.DataFrame(st.session_state.messages)
        csv = chat_data.to_csv(index=False).encode('utf-8')
        st.download_button(label="📥 Download Log Chat", data=csv, file_name=f"log_chat.csv", mime='text/csv', use_container_width=True)

    if st.button("🗑️ Hapus Riwayat Chat", use_container_width=True, type="primary"):
        st.session_state.messages = []
        st.rerun()

# --- 5. INTERFACE CHAT ---
# st.title("🤖 DinasChat Pro")

# Header Atas (Logo dan Judul Kecil)
st.markdown(f"""
    <div class="header-container">
        <div class="header-logo">📄</div>
        <div class="header-text">
            <h1>Klasifikasi Surat KPU Basis Data PKPU 1257</h1>
        </div>
    </div>
""", unsafe_allow_html=True)

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "res_kode" in msg: render_results(msg["res_kode"], "🗂️ Hasil Kode Klasifikasi")
        if "res_jenis" in msg: render_results(msg["res_jenis"], "📄 Hasil Jenis Naskah")

if prompt := st.chat_input("Ketik kata kunci (misal: Kepegawaian)..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Search in both
    res_kode = smart_search(prompt, db_kode, stemmer)
    res_jenis = smart_search(prompt, db_jenis, stemmer)

    with st.chat_message("assistant"):
        if res_kode or res_jenis:
            response_text = "Berikut adalah hasil temuan saya:"
            st.markdown(response_text)
            
            render_results(res_kode, "🗂️ Hasil Kode Klasifikasi")
            render_results(res_jenis, "📄 Hasil Jenis Naskah")
            
            st.session_state.messages.append({
                "role": "assistant", 
                "content": response_text,
                "res_kode": res_kode,
                "res_jenis": res_jenis
            })
        else:
            suggestion = suggest_correction(prompt, db_kode + db_jenis)
            error_msg = f"Maaf, tidak ditemukan data untuk **'{prompt}'**."
            st.error(error_msg)
            
            if suggestion:
                st.markdown(f"💡 Mungkin maksud Anda adalah:")
                if st.button(f"🔍 Cari: {suggestion}", key="btn_suggest"):
                    # Fitur Click-to-Search
                    st.session_state.messages.append({"role": "user", "content": suggestion})
                    st.rerun()
            
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
    st.rerun()