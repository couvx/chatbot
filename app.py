import streamlit as st
import json
import datetime
import os
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from thefuzz import fuzz, process

# --- SETUP NLP ---
@st.cache_resource
def init_nlp():
    factory = StemmerFactory()
    return factory.create_stemmer()

stemmer = init_nlp()

# --- SYNONYM MAPPING ---
SYNONYMS = {
    "nomer": "kode",
    "surat": "naskah",
    "aturan": "peraturan",
    "definisi": "keterangan"
}

# --- DATABASE LOAD ---
@st.cache_data
def load_db():
    # Pastikan file db_kode.json dan db_jenis.json ada di folder yang sama
    with open('db_kode.json', 'r', encoding='utf-8') as f:
        kode_db = json.load(f)
    with open('db_jenis.json', 'r', encoding='utf-8') as f:
        jenis_db = json.load(f)
    return kode_db, jenis_db

# --- LOGGING SYSTEM ---
def log_activity(query, intent, results_count):
    with open("chatbot_log.txt", "a", encoding="utf-8") as f:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] Q: {query} | Intent: {intent} | Found: {results_count}\n")

# --- SEARCH ENGINE ---
def search_engine(query, db):
    # 1. Direct Code Search (Exact)
    direct = [i for i in db if i['kode'].lower() == query.lower()]
    if direct: return direct

    # 2. Lemmatization & Synonym Mapping
    words = query.lower().split()
    mapped_words = [SYNONYMS.get(w, w) for w in words]
    clean_query = stemmer.stem(" ".join(mapped_words))

    # 3. Fuzzy Matching
    results = []
    for item in db:
        # Cari di Klasifikasi & Keterangan
        target_text = f"{item['klasifikasi']} {item['keterangan']}".lower()
        score = fuzz.token_set_ratio(clean_query, target_text)
        
        if score > 70 or clean_query in target_text:
            results.append(item)
    
    return results

# --- STREAMLIT UI ---
st.set_page_config(page_title="DinasChat Pro", page_icon="📝")
st.title("📂 Chatbot Naskah Dinas")

db_kode, db_jenis = load_db()

# State Management
if "messages" not in st.session_state:
    st.session_state.messages = []
if "intent" not in st.session_state:
    st.session_state.intent = None

# Sidebar
with st.sidebar:
    st.header("Admin & Logs")
    if st.button("🔄 Auto-Update (Clear Cache)"):
        st.cache_data.clear()
        st.success("Database di-refresh!")
    
    if os.path.exists("chatbot_log.txt"):
        st.download_button("📥 Download Activity Log", open("chatbot_log.txt", "rb"), "log.txt")

# Chat Interface
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if prompt := st.chat_input("Tanyakan kode atau jenis surat..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Intent Detection
    p_lower = prompt.lower()
    if any(x in p_lower for x in ["kode", "klasifikasi", "pp.", "pl.", "py."]):
        st.session_state.intent = "KODE"
    elif any(x in p_lower for x in ["jenis", "surat", "apa itu", "arti", "maksud"]):
        st.session_state.intent = "JENIS"

    # Search Execution
    target_db = db_kode if st.session_state.intent == "KODE" else db_jenis
    search_results = search_engine(prompt, target_db)

    # Response
    with st.chat_message("assistant"):
        if search_results:
            response_text = f"Ditemukan {len(search_results)} hasil terkait:"
            st.write(response_text)
            for res in search_results[:3]: # Limit 3
                with st.expander(f"{res['kode']} - {res['klasifikasi']}"):
                    st.write(f"**Sifat:** {res['sifat']}")
                    st.write(f"**Keterangan:** {res['keterangan']}")
        else:
            response_text = "Maaf, informasi tidak ditemukan. Coba kata kunci lain."
            st.error(response_text)

    log_activity(prompt, st.session_state.intent, len(search_results))
    st.session_state.messages.append({"role": "assistant", "content": response_text})