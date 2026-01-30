import streamlit as st
import json
import logging
import re
import os
from fuzzywuzzy import fuzz
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

# --- CONFIG & LOGGING ---
st.set_page_config(page_title="Chatbot Naskah Dinas", layout="wide")
logging.basicConfig(filename='chatbot.log', level=logging.INFO, format='%(asctime)s: %(message)s')

# --- ENGINE & DATA LOADING ---
@st.cache_resource
def get_stemmer():
    return StemmerFactory().create_stemmer()

def load_data(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    return []

stemmer = get_stemmer()

# --- HELPER FUNCTIONS ---
def synonym_mapping(text):
    synonyms = {
        "mobil": "kendaraan", "sprint": "perintah", 
        "memo": "nota", "bengkel": "pemeliharaan",
        "hilang": "kehilangan", "asuransi": "masalah"
    }
    for word, replacement in synonyms.items():
        text = text.replace(word, replacement)
    return text

def validate_direct_code(text):
    # Validasi format kode seperti RT.03.2 atau SPt
    return bool(re.match(r'^[A-Za-z0-9.]+$', text))

def search_engine(query, db):
    results = []
    query_clean = stemmer.stem(query.lower())
    query_clean = synonym_mapping(query_clean)
    
    for item in db:
        # 1. Direct Code Search (Skor 100)
        if query.lower() == item['kode'].lower():
            results.append((item, 105)) # Bonus score untuk exact match
            continue
        
        # 2. Fuzzy Matching pada Klasifikasi & Keterangan
        score_klasifikasi = fuzz.token_set_ratio(query_clean, item['klasifikasi'].lower())
        score_ket = fuzz.partial_ratio(query_clean, item['keterangan'].lower())
        final_score = max(score_klasifikasi, score_ket)
        
        if final_score > 65: # Threshold
            results.append((item, final_score))
            
    return sorted(results, key=lambda x: x[1], reverse=True)

# --- SIDEBAR: AUTO-UPDATE & LOGS ---
with st.sidebar:
    st.title("⚙️ Admin Panel")
    st.subheader("Update Database")
    target_db = st.selectbox("Pilih Database", ["db_kode", "db_jenis"])
    uploaded_file = st.file_uploader("Upload JSON Baru", type=['json'])
    
    if uploaded_file and st.button("Update Data"):
        new_data = json.load(uploaded_file)
        with open(f"{target_db}.json", 'w') as f:
            json.dump(new_data, f, indent=4)
        st.success("Database diperbarui!")
        st.rerun()

    if st.checkbox("Lihat Log Pertanyaan"):
        if os.path.exists('chatbot.log'):
            with open('chatbot.log', 'r') as f:
                st.text(f.read()[-500:]) # Tampilkan 500 karakter terakhir

# --- MAIN CHAT INTERFACE ---
st.title("📝 Chatbot Naskah Dinas")
st.info("Gunakan kata kunci seperti 'kode kendaraan', 'jenis surat', atau langsung masukkan kode (misal: RT.03.2)")

# Database Loading
db_kode = load_data('db_kode.json')
db_jenis = load_data('db_jenis.json')

# State Management
if "messages" not in st.session_state: st.session_state.messages = []
if "last_intent" not in st.session_state: st.session_state.last_intent = "KODE"

# Display Messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User Input
if prompt := st.chat_input("Ketik pertanyaan Anda..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. Routing Intent
    p_lower = prompt.lower()
    if any(k in p_lower for k in ['surat', 'jenis', 'naskah', 'nd', 'st', 'spt']):
        intent = "JENIS"
    elif any(k in p_lower for k in ['kode', 'nomor', 'klasifikasi', 'rt.']):
        intent = "KODE"
    else:
        intent = st.session_state.last_intent
    
    st.session_state.last_intent = intent
    current_db = db_kode if intent == "KODE" else db_jenis
    
    # 2. Search & Drill Down
    matches = search_engine(prompt, current_db)
    
    with st.chat_message("assistant"):
        if not matches:
            response = "Maaf, informasi tidak ditemukan di database. Coba kata kunci lain."
            st.error(response)
            logging.info(f"FAILED: {prompt} | Intent: {intent}")
        else:
            logging.info(f"SUCCESS: {prompt} | Found: {len(matches)}")
            
            # Ambil skor tertinggi
            best_match, score = matches[0]
            
            # Logic Drill Down jika ada beberapa kemiripan
            if len(matches) > 1 and score < 100:
                response = f"Saya menemukan beberapa hasil untuk '{prompt}'. Apakah yang Anda maksud salah satu dari ini?"
                st.markdown(response)
                for item, s in matches[:3]: # Tampilkan 3 teratas
                    if st.button(f"📄 {item['kode']} - {item['klasifikasi']}"):
                        # Tampilkan detail saat diklik (Drill Down)
                        st.write(f"**Detail:** {item['keterangan']}")
            else:
                response = f"""
                **Ditemukan pada Database {intent}:**
                - **Kode:** `{best_match['kode']}`
                - **Klasifikasi:** {best_match['klasifikasi']}
                - **Sifat:** {best_match['sifat']}
                - **Keterangan:** {best_match['keterangan']}
                """
                st.markdown(response)
        
    st.session_state.messages.append({"role": "assistant", "content": response})