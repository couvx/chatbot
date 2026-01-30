import streamlit as st
import json
import os
import datetime
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from thefuzz import fuzz

# --- 1. KONFIGURASI ---
st.set_page_config(page_title="DinasChat Pro", page_icon="🤖", layout="centered")

@st.cache_resource
def init_nlp():
    return StemmerFactory().create_stemmer()

@st.cache_data
def load_db():
    try:
        with open('db_kode.json', 'r', encoding='utf-8') as f:
            kode_db = json.load(f)
        with open('db_jenis.json', 'r', encoding='utf-8') as f:
            jenis_db = json.load(f)
        return kode_db, jenis_db
    except:
        return [], []

# --- 2. LOGIKA PENCARIAN CERDAS ---

def smart_search(query, db, stemmer):
    if not db: return []
    
    query_clean = query.lower().strip()
    results = []
    
    for item in db:
        kode = item.get('kode', '').lower()
        klasifikasi = item.get('klasifikasi', '').lower()
        
        score = 0
        # A. Prioritas 1: Kecocokan Kode Persis
        if query_clean == kode:
            score = 100
        # B. Prioritas 2: Kode dimulai dengan input (Misal input 'PP' cocok dengan 'PP.01')
        elif kode.startswith(query_clean):
            score = 90
        # C. Prioritas 3: Input ada di dalam kode (Misal '01' cocok dengan 'PP.01')
        elif query_clean in kode:
            score = 80
        # D. Prioritas 4: Fuzzy matching pada teks klasifikasi
        else:
            score = fuzz.token_set_ratio(query_clean, klasifikasi)

        if score > 50:  # Threshold saran
            item_copy = item.copy()
            item_copy['score'] = score
            results.append(item_copy)
            
    return sorted(results, key=lambda x: x.get('score', 0), reverse=True)

# --- 3. INITIALIZATION ---
stemmer = init_nlp()
db_kode, db_jenis = load_db()

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Halo! Ketik kode (contoh: 'PP') atau jenis surat untuk mencari."}]

# --- 4. UI SIDEBAR ---
with st.sidebar:
    st.title("⚙️ Opsi")
    if st.button("🗑️ Hapus Chat", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "content": "Riwayat dihapus."}]
        st.rerun()

# --- 5. INTERFACE CHAT ---
st.title("🤖 DinasChat Pro")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "results" in msg:
            for r in msg["results"]:
                with st.expander(f"📍 {r.get('kode')} - {r.get('klasifikasi')}"):
                    st.write(f"**Keterangan:** {r.get('keterangan')}")

if prompt := st.chat_input("Masukkan kode atau kata kunci..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Logika Penentuan Database (Intent)
    p = prompt.lower()
    # Jika input pendek atau mengandung angka, asumsikan mencari KODE
    is_short_code = len(p) <= 5 or any(char.isdigit() for char in p)
    
    if is_short_code or any(x in p for x in ["pp", "pl", "py", "kode"]):
        db_to_search = db_kode
        target_name = "Kode Klasifikasi"
    else:
        db_to_search = db_jenis
        target_name = "Jenis Naskah"

    results = smart_search(prompt, db_to_search, stemmer)

    with st.chat_message("assistant"):
        if results:
            # Jika skor tertinggi tidak 100%, katakan "Mungkin maksud Anda..."
            header = "Ditemukan hasil berikut:" if results[0]['score'] == 100 else "Saya menemukan beberapa saran yang mirip:"
            st.markdown(f"**{header}**")
            
            top_results = results[:5]
            for r in top_results:
                with st.expander(f"📍 {r.get('kode')} - {r.get('klasifikasi')}"):
                    st.write(f"**Sifat:** {r.get('sifat', '-')}")
                    st.info(f"**Keterangan:** {r.get('keterangan', '-')}")
            
            st.session_state.messages.append({"role": "assistant", "content": header, "results": top_results})
        else:
            msg_fail = "Tidak ditemukan hasil yang mirip. Coba masukkan kode lain."
            st.error(msg_fail)
            st.session_state.messages.append({"role": "assistant", "content": msg_fail})

    st.rerun()