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
    except Exception:
        return [], []

def smart_search(query, db, stemmer):
    if not db: return []
    query_clean = query.lower().strip()
    query_stemmed = stemmer.stem(query_clean)
    scored_results = []
    for item in db:
        content = f"{item.get('klasifikasi', '')} {item.get('keterangan', '')}".lower()
        score = 0
        if query_clean == item.get('kode', '').lower(): score = 100
        else: score = fuzz.token_set_ratio(query_clean, content)
        if score > 65:
            item_copy = item.copy()
            item_copy['score'] = score
            scored_results.append(item_copy)
    return sorted(scored_results, key=lambda x: x['score'], reverse=True)

# --- 3. INITIALIZATION ---
stemmer = init_nlp()
db_kode, db_jenis = load_db()

if "messages" not in st.session_state:
    st.session_state.messages = []

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

# --- 5. MAIN UI RENDERER ---

# Header Atas (Logo dan Judul Kecil)
st.markdown(f"""
    <div class="header-container">
        <div class="header-logo">📄</div>
        <div class="header-text">
            <h1>Klasifikasi Surat KPU</h1>
            <p>Basis Data PKPU 1257</p>
        </div>
    </div>
""", unsafe_allow_html=True)

# Tampilan Landing Page (Hanya jika belum ada chat)
if not st.session_state.messages:
    st.markdown("""
        <div class="landing-container">
            <div class="landing-icon">📄</div>
            <h2>Klasifikasi Arsip KPU</h2>
            <p>Tanyakan Kode Klasifikasi dan Sifat Naskah (Biasa/Rahasia) berdasarkan PKPU 1257. Silakan ketik perihal surat Anda di bawah ini.</p>
        </div>
    """, unsafe_allow_html=True)
else:
    # Tampilkan Chat jika sudah ada percakapan
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "res_kode" in msg:
                for r in msg["res_kode"][:3]:
                    with st.expander(f"📍 {r.get('kode')} - {r.get('klasifikasi')}"):
                        st.info(r.get('keterangan'))

# Input Chat
if prompt := st.chat_input("Contoh: Kode dan sifat surat pelantikan KPPS..."):
    # Simpan pesan user
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Cari data
    res_k = smart_search(prompt, db_kode, stemmer)
    res_j = smart_search(prompt, db_jenis, stemmer)
    
    # Simpan respon asisten
    response = "Berikut hasil pencarian saya:" if (res_k or res_j) else "Data tidak ditemukan."
    st.session_state.messages.append({
        "role": "assistant", 
        "content": response,
        "res_kode": res_k,
        "res_jenis": res_j
    })
    st.rerun()

# Footer di bawah input bar
st.markdown('<p class="input-footer">Hasil berdasarkan AI. Selalu verifikasi dengan dokumen fisik PKPU 1257.</p>', unsafe_allow_html=True)