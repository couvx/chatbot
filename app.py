import streamlit as st
import json
import os
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from thefuzz import fuzz

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="DinasChat Pro", page_icon="🤖", layout="centered")

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
    """Mencari saran kata kunci dari database spesifik"""
    words_pool = set()
    for item in db:
        content = f"{item.get('klasifikasi', '')} {item.get('keterangan', '')}".lower()
        words_pool.update("".join([c for c in content if c.isalnum() or c.isspace()]).split())
    
    best_match = None
    highest_ratio = 0
    for word in words_pool:
        if len(word) < 4: continue
        ratio = fuzz.ratio(query.lower(), word)
        if ratio > highest_ratio:
            highest_ratio = ratio
            best_match = word
            
    return best_match if 75 <= highest_ratio < 100 else None

def get_smart_intent(prompt):
    p = prompt.lower()
    clean_words = set("".join([c for c in p if c.isalnum() or c.isspace()]).split())
    if clean_words.intersection({"kode", "klasifikasi", "pp", "pl", "py", "nomor", "no"}):
        return "KODE"
    elif clean_words.intersection({"jenis", "surat", "apa", "maksud", "arti", "pengertian", "definisi", "naskah"}):
        return "JENIS"
    return "GLOBAL"

def smart_search(query, db, stemmer):
    if not db: return []
    query_clean = query.lower().strip()
    query_stemmed = stemmer.stem(query_clean)
    scored_results = []
    
    for item in db:
        klasifikasi = item.get('klasifikasi', '').lower()
        keterangan = item.get('keterangan', '').lower()
        kode = item.get('kode', '').lower()
        full_text = f"{klasifikasi} {keterangan}"
        
        score = 0
        if query_clean == kode: score += 100 
        elif query_clean in kode: score += 60
        
        score += fuzz.token_set_ratio(query_clean, full_text)
        if query_stemmed in full_text: score += 15
        
        if score > 65:
            item_copy = item.copy()
            item_copy['score'] = min(score, 100)
            scored_results.append(item_copy)
            
    return sorted(scored_results, key=lambda x: (-x['score'], x.get('kode', '')))

# --- 3. INITIALIZATION ---
stemmer = init_nlp()
db_kode, db_jenis = load_db()

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Halo! Silakan tanya tentang **Kode Klasifikasi** atau **Jenis Surat**."}]

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("⚙️ Panel Kontrol")
    if st.button("🗑️ Hapus Riwayat Chat", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "content": "Riwayat dihapus."}]
        st.rerun()

# --- 5. INTERFACE CHAT ---
st.title("🤖 DinasChat Pro")

# Render Riwayat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "results" in msg:
            for r in msg["results"]:
                with st.expander(f"📍 {r.get('kode', 'N/A')} - {r.get('klasifikasi', 'Detail')}"):
                    st.write(f"**Sifat:** {r.get('sifat', '-')}")
                    st.info(f"**Keterangan:** {r.get('keterangan', '-')}")

# Input User
if prompt := st.chat_input("Ketik pertanyaan Anda..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

# Logika Pemrosesan Pesan Terakhir
if len(st.session_state.messages) > 0 and st.session_state.messages[-1]["role"] == "user":
    last_prompt = st.session_state.messages[-1]["content"]
    intent = get_smart_intent(last_prompt)
    
    # Pilih DB & Label berdasarkan intent
    if intent == "KODE":
        target_db, label = db_kode, "Daftar Kode Klasifikasi"
    elif intent == "JENIS":
        target_db, label = db_jenis, "Jenis Naskah Dinas"
    else:
        target_db, label = db_kode + db_jenis, "Informasi Terkait"

    results = smart_search(last_prompt, target_db, stemmer)

    with st.chat_message("assistant"):
        if results:
            res_text = f"Ditemukan hasil pada kategori **{label}**:"
            st.markdown(res_text)
            top_res = results[:5]
            for r in top_res:
                with st.expander(f"📍 {r.get('kode', 'N/A')} - {r.get('klasifikasi', 'Detail')}"):
                    st.write(f"**Sifat:** {r.get('sifat', '-')}")
                    st.info(f"**Keterangan:** {r.get('keterangan', '-')}")
            st.session_state.messages.append({"role": "assistant", "content": res_text, "results": top_res})
        else:
            suggestion = suggest_correction(last_prompt, target_db)
            err_msg = f"Data tidak ditemukan di kategori **{intent}**."
            st.error(err_msg)
            
            if suggestion:
                st.markdown(f"Mungkin maksud Anda adalah: **{suggestion}**")
                # FITUR CLICK TO SEARCH
                if st.button(f"🔍 Cari: {suggestion}", key="btn_suggest"):
                    st.session_state.messages.append({"role": "user", "content": suggestion})
                    st.rerun()
            
            st.session_state.messages.append({"role": "assistant", "content": err_msg})