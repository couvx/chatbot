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

def suggest_correction(query, db):
    """Mencari saran kata kunci jika terjadi typo (Auto-Correction Logic)"""
    words_pool = set()
    for item in db:
        # Ambil kata-kata dari klasifikasi dan keterangan untuk membangun kamus
        content = f"{item.get('klasifikasi', '')} {item.get('keterangan', '')}".lower()
        # Bersihkan simbol dan ambil kata unik
        words_pool.update("".join([c for c in content if c.isalnum() or c.isspace()]).split())
    
    best_match = None
    highest_ratio = 0
    
    for word in words_pool:
        if len(word) < 4: continue # Abaikan kata yang terlalu pendek
        ratio = fuzz.ratio(query.lower(), word)
        if ratio > highest_ratio:
            highest_ratio = ratio
            best_match = word
            
    # Kembalikan saran jika kemiripan antara 70% - 99% (bukan exact match)
    if highest_ratio > 70 and highest_ratio < 100:
        return best_match
    return None

def get_smart_intent(prompt):
    """Mendeteksi intent: 'KODE', 'JENIS', atau 'GLOBAL'"""
    p = prompt.lower()
    clean_words = set("".join([c for c in p if c.isalnum() or c.isspace()]).split())
    
    keywords_kode = {"kode", "klasifikasi", "pp", "pl", "py", "nomor", "no"}
    keywords_jenis = {"jenis", "surat", "apa", "maksud", "arti", "pengertian", "definisi", "naskah"}

    if clean_words.intersection(keywords_kode):
        return "KODE"
    elif clean_words.intersection(keywords_jenis):
        return "JENIS"
    return "GLOBAL"

def smart_search(query, db, stemmer):
    """Pencarian dengan Skoring Multi-Layer"""
    if not db: return []
    
    query_clean = query.lower().strip()
    query_stemmed = stemmer.stem(query_clean)
    query_words = set(query_clean.split())
    scored_results = []
    
    for item in db:
        klasifikasi = item.get('klasifikasi', '').lower()
        keterangan = item.get('keterangan', '').lower()
        kode = item.get('kode', '').lower()
        full_text = f"{klasifikasi} {keterangan}"
        
        score = 0
        if query_clean == kode:
            score += 100 
        elif query_clean in kode:
            score += 60
            
        text_score = fuzz.token_set_ratio(query_clean, full_text)
        
        stem_bonus = 15 if query_stemmed in full_text else 0
        keyword_bonus = 10 if any(word in klasifikasi for word in query_words) else 0

        final_score = score + text_score + stem_bonus + keyword_bonus
        
        if final_score > 65: # Threshold disesuaikan
            item_copy = item.copy()
            item_copy['score'] = min(final_score, 100)
            scored_results.append(item_copy)
            
    return sorted(scored_results, key=lambda x: (-x['score'], x.get('kode', '')))

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

    intent = get_smart_intent(prompt)
    
    # Filter Database
    if intent == "KODE":
        current_db = db_kode
        context_msg = "Mencari di Database Kode Klasifikasi..."
    elif intent == "JENIS":
        current_db = db_jenis
        context_msg = "Mencari di Database Jenis Naskah/Surat..."
    else:
        current_db = db_kode + db_jenis
        context_msg = "Mencari informasi relevan..."

    results = smart_search(prompt, current_db, stemmer)

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
            
            st.session_state.messages.append({"role": "assistant", "content": response_text, "results": top_results})
        else:
            # JIKA TIDAK ADA HASIL, CARI SARAN KOREKSI
            suggestion = suggest_correction(prompt, current_db)
            error_msg = f"Maaf, saya tidak menemukan data untuk kata kunci **'{prompt}'**."
            st.error(error_msg)
            
            if suggestion:
                st.info(f"💡 Mungkin maksud Anda: **{suggestion}**?")
            
            st.session_state.messages.append({"role": "assistant", "content": error_msg})

    st.rerun()