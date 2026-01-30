import streamlit as st
import json
import os
import pandas as pd
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from thefuzz import fuzz
from datetime import datetime

# --- 1. KONFIGURASI HALAMAN & TEMA TERANG ---
st.set_page_config(page_title="DinasChat Pro", page_icon="🤖", layout="centered")

# Custom CSS untuk memaksa Tema Terang dan mengatur Sidebar
st.markdown("""
    <style>
    /* Memaksa background putih pada seluruh aplikasi */
    .stApp {
        background-color: white;
        color: black;
    }
    
    /* Mengatur warna Sidebar tetap terang */
    [data-testid="stSidebar"] {
        background-color: #f8f9fa;
        border-right: 1px solid #e0e0e0;
    }

    /* Label PERCAKAPAN */
    .sidebar-label {
        font-size: 0.75rem;
        font-weight: 800;
        color: #94a3b8;
        letter-spacing: 0.1rem;
        margin-bottom: 10px;
        margin-top: 10px;
    }

    /* Styling tombol agar lebih rapi */
    .stButton > button {
        border-radius: 8px;
        text-align: left;
    }
    
    /* Container untuk menaruh tombol di bagian bawah sidebar */
    .sidebar-footer {
        position: fixed;
        bottom: 20px;
        width: 260px;
    }
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

# --- 4. SIDEBAR MODIFIKASI ---
with st.sidebar:
    # 1. Chat Aktif di Bagian Atas
    st.markdown('<div class="sidebar-label">PERCAKAPAN</div>', unsafe_allow_html=True)
    st.button("💬 Chat Aktif", use_container_width=True, type="secondary")
    
    # Elemen kosong untuk mendorong tombol lain ke bawah
    # (Menggunakan CSS position fixed untuk kestabilan posisi bawah)
    st.markdown('<div style="height: 60vh;"></div>', unsafe_allow_html=True)
    
    # 2. Container Bawah untuk Download dan Hapus
    st.divider()
    
    # Tombol Download Log
    if st.session_state.messages:
        chat_data = pd.DataFrame(st.session_state.messages)
        csv = chat_data.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Log Chat",
            data=csv,
            file_name=f"log_{datetime.now().strftime('%d%m%y')}.csv",
            mime='text/csv',
            use_container_width=True
        )

    # Tombol Hapus Riwayat (Aksen Merah/Primary)
    if st.button("🗑️ Hapus Riwayat Chat", use_container_width=True, type="primary"):
        st.session_state.messages = [{"role": "assistant", "content": "Riwayat telah dibersihkan."}]
        st.rerun()

# --- 5. UI RENDERER ---
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

# --- 6. INTERFACE CHAT ---
st.title("🤖 DinasChat Pro")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "res_kode" in msg: render_results(msg["res_kode"], "🗂️ Hasil Kode Klasifikasi")
        if "res_jenis" in msg: render_results(msg["res_jenis"], "📄 Hasil Jenis Naskah")

if prompt := st.chat_input("Ketik kata kunci (misal: Kepegawaian)..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

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
            error_msg = f"Maaf, tidak ditemukan data untuk **'{prompt}'**."
            st.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
    st.rerun()