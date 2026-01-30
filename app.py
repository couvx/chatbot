import streamlit as st
import json
import os
import datetime
from sastrawi.stemmer.stemmer_factory import StemmerFactory
from thefuzz import fuzz, process

# --- 1. STATE MANAGEMENT & LOGGING ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "context" not in st.session_state:
    st.session_state.context = None # Menyimpan 'KODE' atau 'JENIS'

def write_log(query, intent, found):
    with open("bot_logs.txt", "a", encoding="utf-8") as f:
        tgl = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{tgl}] Q: {query} | Intent: {intent} | Found: {found}\n")

# --- 2. NLP & DB ENGINE ---
@st.cache_resource
def init_nlp():
    return StemmerFactory().create_stemmer()

@st.cache_data
def load_databases():
    # Pastikan file json ada atau buat dummy jika tidak ada
    with open('db_kode.json', 'r') as f: k = json.load(f)
    with open('db_jenis.json', 'r') as f: j = json.load(f)
    return k, j

stemmer = init_nlp()
db_kode, db_jenis = load_databases()

def smart_search(query, db):
    # a. Direct Code Search (Exact Match)
    query_upper = query.upper().strip()
    direct = [i for i in db if i['kode'].upper() == query_upper]
    if direct: return direct, "Direct Search"

    # b. Lemmatization (Bahasa Indonesia)
    stemmed_query = stemmer.stem(query)

    # c. Fuzzy Matching & Keyword Mapping
    results = []
    for item in db:
        # Gabungkan semua info untuk dicarikan kemiripan
        content = f"{item['kode']} {item['klasifikasi']} {item['keterangan']}".lower()
        
        # Skor kemiripan
        score = fuzz.partial_ratio(stemmed_query, content)
        if score > 75 or stemmed_query in content:
            results.append(item)
    
    return results, "Fuzzy/Keyword"

# --- 3. UI STREAMLIT ---
st.set_page_config(page_title="DinasChat AI", layout="wide")
st.title("📂 Chatbot Klasifikasi & Naskah Dinas")

# Sidebar untuk Auto-Update & Log
with st.sidebar:
    st.header("Admin Dashboard")
    if st.button("🔄 Refresh/Auto-Update DB"):
        st.cache_data.clear()
        st.success("Database Disinkronkan!")
    
    if os.path.exists("bot_logs.txt"):
        st.download_button("📥 Download Logs", open("bot_logs.txt").read(), "logs.txt")

# Chat Interface
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Contoh: 'Apa arti Notula?' atau 'Cari kode PP.01'"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # Logic: Intent Detection
    clean_p = prompt.lower()
    if any(x in clean_p for x in ["kode", "klasifikasi", "pp.", "pl.", "py."]):
        st.session_state.context = "KODE"
    elif any(x in clean_p for x in ["jenis", "naskah", "surat", "apa itu", "arti"]):
        st.session_state.context = "JENIS"

    # Execution
    target_db = db_kode if st.session_state.context == "KODE" else db_jenis
    res, method = smart_search(prompt, target_db)

    # Response Building
    with st.chat_message("assistant"):
        if res:
            header = "🔢 Klasifikasi Ditemukan:" if st.session_state.context == "KODE" else "📝 Jenis Naskah Ditemukan:"
            st.markdown(f"### {header}")
            for r in res[:3]:
                with st.expander(f"{r['kode']} - {r['klasifikasi']}", expanded=True):
                    st.write(f"**Sifat:** {r['sifat']}")
                    st.write(f"**Keterangan:** {r['keterangan']}")
            full_res = "Success"
        else:
            st.error("Data tidak ditemukan. Coba gunakan kata kunci lain.")
            full_res = "Not Found"
    
    write_log(prompt, st.session_state.context, full_res)
    st.session_state.messages.append({"role": "assistant", "content": f"Pencarian selesai via {method}"})