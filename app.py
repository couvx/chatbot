import streamlit as st
import json
import os
import datetime
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from thefuzz import fuzz

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="DinasChat Pro", page_icon="🤖", layout="centered")

# --- 2. CORE FUNCTIONS (NLP & DATABASE) ---

@st.cache_resource
def init_nlp():
    """Inisialisasi Stemmer Bahasa Indonesia"""
    return StemmerFactory().create_stemmer()

@st.cache_data
def load_db():
    """Memuat database JSON secara terpisah"""
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

def get_smart_intent(prompt):
    """
    Mendeteksi intent secara tegas. 
    Mengembalikan: 'KODE', 'JENIS', atau 'GLOBAL'
    """
    p = prompt.lower()
    # Pembersihan teks untuk pencocokan kata kunci
    clean_words = set("".join([c for c in p if c.isalnum() or c.isspace()]).split())
    
    # Kamus Spesifik
    keywords_kode = {"kode", "klasifikasi", "pp", "pl", "py", "nomor", "no"}
    keywords_jenis = {"jenis", "surat", "apa", "maksud", "arti", "pengertian", "definisi", "naskah"}

    # Logika Prioritas
    if clean_words.intersection(keywords_kode):
        return "KODE"
    elif clean_words.intersection(keywords_jenis):
        return "JENIS"
    return "GLOBAL"

def smart_search(query, db, stemmer):
    """Pencarian dengan Scoring & Ranking"""
    if not db: return []
    
    query_clean = query.lower().strip()
    query_stemmed = stemmer.stem(query_clean)
    scored_results = []
    
    for item in db:
        content = f"{item.get('klasifikasi', '')} {item.get('keterangan', '')}".lower()
        kode = item.get('kode', '').lower()
        
        # Scoring
        score = fuzz.token_set_ratio(query_clean, content)
        if query_clean in kode: score += 40
        if query_stemmed in content: score += 15

        if score > 60:
            item_copy = item.copy()
            item_copy['score'] = min(score, 100)
            scored_results.append(item_copy)
            
    return sorted(scored_results, key=lambda x: x.get('score', 0), reverse=True)

# --- 3. INITIALIZATION ---
stemmer = init_nlp()
db_kode, db_jenis = load_db()

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Halo! Saya asisten khusus naskah dinas. Silakan tanya tentang **Kode Klasifikasi** atau **Jenis Surat**."}]

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("⚙️ Panel Kontrol")
    if st.button("🗑️ Hapus Riwayat Chat", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "content": "Riwayat dihapus. Ada yang bisa saya bantu?"}]
        st.rerun()
    st.divider()
    st.caption("Database Terdeteksi:")
    st.write(f"- DB Kode: {len(db_kode)} data")
    st.write(f"- DB Jenis: {len(db_jenis)} data")

# --- 5. INTERFACE CHAT ---
st.title("🤖 DinasChat Pro")

# Render Riwayat Chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "results" in msg and msg["results"]:
            for r in msg["results"]:
                s = r.get('score', 0)
                clr = "green" if s > 85 else "orange"
                with st.expander(f"📍 {r.get('kode', 'N/A')} - {r.get('klasifikasi', 'Detail')}"):
                    st.markdown(f":{clr}[**Relevansi: {s}%**]")
                    st.write(f"**Sifat:** {r.get('sifat', '-')}")
                    st.info(f"**Keterangan:** {r.get('keterangan', '-')}")

# Input User
if prompt := st.chat_input("Ketik pertanyaan Anda..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 1. Deteksi Intent (Strict)
    intent = get_smart_intent(prompt)
    
    # 2. Filter Database berdasarkan Intent
    if intent == "KODE":
        results = smart_search(prompt, db_kode, stemmer)
        context_msg = "Mencari di Database Kode Klasifikasi..."
    elif intent == "JENIS":
        results = smart_search(prompt, db_jenis, stemmer)
        context_msg = "Mencari di Database Jenis Naskah/Surat..."
    else:
        # Jika tidak terdeteksi, cari di keduanya
        results = smart_search(prompt, db_kode, stemmer) + smart_search(prompt, db_jenis, stemmer)
        results = sorted(results, key=lambda x: x.get('score', 0), reverse=True)
        context_msg = "Mencari informasi relevan..."

    # 3. Jawaban Assistant
    with st.chat_message("assistant"):
        if results:
            top_results = results[:5]
            response_text = f"**{context_msg}**\nDitemukan {len(results)} hasil yang cocok:"
            st.markdown(response_text)
            
            for r in top_results:
                s = r.get('score', 0)
                clr = "green" if s > 85 else "orange"
                with st.expander(f"📍 {r.get('kode', 'N/A')} - {r.get('klasifikasi', 'Detail')}"):
                    st.markdown(f":{clr}[**Relevansi: {s}%**]")
                    st.write(f"**Sifat:** {r.get('sifat', '-')}")
                    st.info(f"**Keterangan:** {r.get('keterangan', '-')}")
            
            st.session_state.messages.append({
                "role": "assistant", 
                "content": response_text, 
                "results": top_results
            })
        else:
            error_msg = f"Maaf, saya tidak menemukan data di kategori **{intent}**. Coba gunakan kata kunci yang lebih spesifik."
            st.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})

    st.rerun()