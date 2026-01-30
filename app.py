import streamlit as st
import json
import logging
from fuzzywuzzy import fuzz
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Bot Naskah Dinas", page_icon="📝")

# --- INISIALISASI ENGINE (Caching agar cepat) ---
@st.cache_resource
def load_nlp():
    factory = StemmerFactory()
    return factory.create_stemmer()

@st.cache_data
def load_db():
    with open('db_jenis.json', 'r') as f: jenis = json.load(f)
    with open('db_kode.json', 'r') as f: kode = json.load(f)
    return jenis, kode

stemmer = load_nlp()
db_jenis, db_kode = load_db()

# --- FUNGSI PENDUKUNG ---
def synonym_mapper(text):
    mapping = {
        "mobil": "kendaraan",
        "sprint": "surat perintah",
        "memo": "nota dinas",
        "hilang": "kehilangan"
    }
    for word, replacement in mapping.items():
        text = text.replace(word, replacement)
    return text

def search_logic(query, db):
    results = []
    query_clean = stemmer.stem(query.lower())
    query_clean = synonym_mapper(query_clean)
    
    for item in db:
        # 1. Direct Code Search (Skor Tertinggi)
        if query.lower() in item['kode'].lower():
            results.append((item, 100))
            continue
            
        # 2. Fuzzy Matching pada Klasifikasi & Keterangan
        score_klasifikasi = fuzz.partial_ratio(query_clean, item['klasifikasi'].lower())
        score_ket = fuzz.partial_ratio(query_clean, item['keterangan'].lower())
        max_score = max(score_klasifikasi, score_ket)
        
        if max_score > 60: # Threshold akurasi
            results.append((item, max_score))
            
    # Urutkan berdasarkan skor kemiripan tertinggi
    results.sort(key=lambda x: x[1], reverse=True)
    return [r[0] for r in results]

# --- UI STREAMLIT ---
st.title("🤖 Chatbot Naskah Dinas")
st.markdown("Tanya mengenai **Jenis Surat** atau **Kode Klasifikasi**.")

# State Management untuk Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_intent" not in st.session_state:
    st.session_state.last_intent = None

# Tampilkan chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input User
if prompt := st.chat_input("Contoh: 'Apa kode untuk perbaikan mobil?'"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # --- LOGIKA ROUTING ---
    processed_prompt = prompt.lower()
    
    # Penentuan Intent (Database mana yang dibuka)
    if any(k in processed_prompt for k in ['kode', 'nomor', 'rt', '03']):
        intent = "KODE"
        current_db = db_kode
    elif any(k in processed_prompt for k in ['surat', 'jenis', 'naskah', 'nd', 'st']):
        intent = "JENIS"
        current_db = db_jenis
    else:
        # Jika ambigu, gunakan intent sebelumnya
        intent = st.session_state.last_intent or "KODE"
        current_db = db_kode if intent == "KODE" else db_jenis

    st.session_state.last_intent = intent
    
    # Pencarian
    results = search_logic(prompt, current_db)
    
    # Response Generation
    with st.chat_message("assistant"):
        if results:
            res = results[0] # Ambil hasil terbaik
            full_res = f"**Hasil Pencarian ({intent}):**\n\n"
            full_res += f"**Kode:** `{res['kode']}`\n\n"
            full_res += f"**Klasifikasi:** {res['klasifikasi']}\n\n"
            full_res += f"**Sifat:** {res['sifat']}\n\n"
            full_res += f"**Keterangan:** {res['keterangan']}"
            
            if len(results) > 1:
                full_res += f"\n\n---\n*Mungkin yang Anda maksud lainnya: {results[1]['kode']} - {results[1]['klasifikasi']}*"
        else:
            full_res = "Maaf, saya tidak menemukan kode atau jenis naskah yang relevan. Mohon coba kata kunci lain."
            logging.warning(f"Gagal mencari: {prompt}")

        st.markdown(full_res)
        st.session_state.messages.append({"role": "assistant", "content": full_res})