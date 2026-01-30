import streamlit as st
import json
import os
import pandas as pd
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from thefuzz import fuzz
from datetime import datetime

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Klasifikasi Surat KPU", page_icon="📄", layout="wide")

# Custom CSS untuk menyamakan style dengan gambar
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stChatMessage { border-radius: 15px; margin-bottom: 10px; }
    .welcome-container {
        display: flex; flex-direction: column; align-items: center;
        justify-content: center; text-align: center; padding: 100px 20px;
    }
    .welcome-icon { font-size: 50px; color: #d32f2f; margin-bottom: 20px; }
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
        return [], []

def smart_search(query, db, stemmer):
    if not db: return []
    query_clean = query.lower().strip()
    query_stemmed = stemmer.stem(query_clean)
    scored_results = []
    
    for item in db:
        content = f"{item.get('klasifikasi', '')} {item.get('keterangan', '')}".lower()
        kode = item.get('kode', '').lower()
        
        score = 0
        if query_clean == kode: score += 100
        elif query_clean in kode: score += 60
        
        text_score = fuzz.token_set_ratio(query_clean, content)
        stem_bonus = 15 if query_stemmed in content else 0
        
        final_score = min(score + text_score + stem_bonus, 100)
        if final_score >= 75: # Sesuai permintaan: Tetap tampilkan 75%-100%
            item_copy = item.copy()
            item_copy['score'] = final_score
            scored_results.append(item_copy)
            
    return sorted(scored_results, key=lambda x: x['score'], reverse=True)

# --- 3. INITIALIZATION & SESSION STATE ---
stemmer = init_nlp()
db_kode, db_jenis = load_db()

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("🏠 Menu Utama")
    st.write("---")
    st.write("PERCAKAPAN")
    st.button("💬 Chat Aktif", use_container_width=True, type="primary")
    
    st.spacer = st.container()
    st.write("---")
    
    # Fitur Download Log Chat
    if st.session_state.messages:
        chat_data = [{"Waktu": datetime.now().strftime("%H:%M"), "Role": m["role"], "Pesan": m["content"]} for m in st.session_state.messages]
        df_log = pd.DataFrame(chat_data)
        csv = df_log.to_csv(index=False).encode('utf-8')
        st.download_button(label="📥 Download Log Chat", data=csv, file_name=f"log_chat_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", mime="text/csv", use_container_width=True)
    
    if st.button("🗑️ Hapus Riwayat Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    
    st.caption("Versi 1.1.0 - PKPU 1257")

# --- 5. MAIN UI ---
# Header tetap muncul
col1, col2 = st.columns([0.1, 0.9])
with col1:
    st.image("https://upload.wikimedia.org/wikipedia/commons/4/46/KPU_Logo.svg", width=50) # Opsional: Logo KPU
with col2:
    st.markdown("### **Klasifikasi Surat KPU**")
    st.caption("Basis Data PKPU 1257")

# Kondisi Tampilan: Landing Page vs Chat History
if not st.session_state.messages:
    st.markdown(f"""
        <div class="welcome-container">
            <div class="welcome-icon">📄</div>
            <h2>Klasifikasi Arsip KPU</h2>
            <p>Tanyakan <b>**Kode Klasifikasi**</b> dan <b>**Sifat Naskah**</b><br>
            (Biasa/Rahasia) berdasarkan PKPU 1257. Silakan ketik<br>
            perihal surat Anda di bawah ini.</p>
        </div>
        """, unsafe_allow_html=True)
else:
    def render_results(results, title):
        if results:
            st.subheader(title)
            for r in results[:3]:
                s = r.get('score', 0)
                clr = "green" if s > 85 else "orange"
                with st.expander(f"📍 {r.get('kode', 'N/A')} - {r.get('klasifikasi', 'Detail')}"):
                    st.markdown(f":{clr}[**Relevansi: {s}%**]")
                    st.write(f"**Sifat:** {r.get('sifat', '-')}")
                    st.info(f"**Keterangan:** {r.get('keterangan', '-')}")
            st.divider()

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "res_kode" in msg: render_results(msg["res_kode"], "🗂️ Hasil Kode Klasifikasi")
            if "res_jenis" in msg: render_results(msg["res_jenis"], "📄 Hasil Jenis Naskah")

# --- 6. CHAT INPUT ---
if prompt := st.chat_input("Contoh: Kode dan sifat surat pelantikan KPPS..."):
    # Simpan pesan user
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Cari data
    res_kode = smart_search(prompt, db_kode, stemmer)
    res_jenis = smart_search(prompt, db_jenis, stemmer)
    
    # Logika Assistant
    if res_kode or res_jenis:
        response_text = "Berikut adalah hasil temuan saya (Akurasi 75-100%):"
        st.session_state.messages.append({
            "role": "assistant", 
            "content": response_text,
            "res_kode": res_kode,
            "res_jenis": res_jenis
        })
    else:
        error_msg = f"Maaf, tidak ditemukan data yang cocok (min. 75%) untuk **'{prompt}'**."
        st.session_state.messages.append({"role": "assistant", "content": error_msg})
    
    st.rerun()

st.markdown("<center><p style='color: gray; font-size: 10px;'>Hasil berdasarkan AI. Selalu verifikasi dengan dokumen fisik PKPU 1257.</p></center>", unsafe_allow_html=True)