import streamlit as st
import json
from sastrawi.stemmer.stemmer_factory import StemmerFactory
from thefuzz import fuzz, process

# --- CONFIG ---
st.set_page_config(page_title="DinasChat AI", page_icon="📝")

# --- LOAD DATA & NLP TOOLS ---
@st.cache_resource
def get_nlp_tools():
    factory = StemmerFactory()
    return factory.create_stemmer()

@st.cache_data
def load_all_db():
    with open('db_kode.json', 'r') as f: k = json.load(f)
    with open('db_jenis.json', 'r') as f: j = json.load(f)
    return k, j

stemmer = get_nlp_tools()
db_kode, db_jenis = load_all_db()

# --- SEARCH ENGINE & FUZZY LOGIC ---
def search_engine(query, database):
    query = query.lower()
    
    # 1. Direct Code Search (Exact)
    direct = [i for i in database if i['kode'].lower() == query]
    if direct: return direct
    
    # 2. Fuzzy Matching & Keyword Search
    # Mencari kemiripan pada field 'kode', 'klasifikasi', dan 'keterangan'
    results = []
    for item in database:
        # Gabungkan field untuk pencarian teks
        target_text = f"{item['kode']} {item['klasifikasi']} {item['keterangan']}".lower()
        
        # Cek Keyword Match
        if query in target_text:
            results.append(item)
            continue
            
        # Cek Fuzzy Match Score
        score = fuzz.partial_ratio(query, target_text)
        if score > 80: # Ambang batas kecocokan
            results.append(item)
            
    return results

# --- UI LAYOUT ---
st.title("🤖 Chatbot Naskah Dinas")
st.markdown("---")

# State Management for Intent & History
if "messages" not in st.session_state:
    st.session_state.messages = []
if "intent_context" not in st.session_state:
    st.session_state.intent_context = None

# Sidebar untuk Log & Status
with st.sidebar:
    st.header("⚙️ Sistem Status")
    st.write(f"**Konteks Aktif:** {st.session_state.intent_context if st.session_state.intent_context else 'Netral'}")
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.session_state.intent_context = None
        st.rerun()

# Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- CORE CHAT LOGIC ---
if prompt := st.chat_input("Tanyakan kode (ex: PP.01) atau jenis (ex: Laporan)..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 1. Preprocessing (Lemmatization)
    clean_query = stemmer.stem(prompt.lower())

    # 2. Intent Detection (State Management)
    # Jika user tanya tentang kode/klasifikasi
    if any(x in clean_query for x in ["kode", "klasifikasi", "nomor", "angka"]):
        st.session_state.intent_context = "KODE"
    # Jika user tanya tentang jenis/surat/naskah
    elif any(x in clean_query for x in ["jenis", "surat", "naskah", "arti", "maksud"]):
        st.session_state.intent_context = "JENIS"

    # 3. Decision Making Berdasarkan Intent
    final_results = []
    header_text = ""

    if st.session_state.intent_context == "KODE":
        final_results = search_engine(prompt, db_kode)
        header_text = "🔍 **Hasil Klasifikasi Kode**"
    elif st.session_state.intent_context == "JENIS":
        final_results = search_engine(prompt, db_jenis)
        header_text = "📄 **Detail Jenis Naskah**"
    else:
        # Jika intent belum terdeteksi, coba cari di keduanya
        res_k = search_engine(prompt, db_kode)
        res_j = search_engine(prompt, db_jenis)
        final_results = res_k + res_j
        header_text = "🔎 **Hasil Pencarian Umum**"

    # 4. Generate Response
    with st.chat_message("assistant"):
        if final_results:
            st.markdown(header_text)
            for res in final_results[:3]: # Limit 3 hasil teratas
                with st.expander(f"{res['kode']} - {res['klasifikasi']}", expanded=True):
                    st.write(f"**Sifat:** {res['sifat']}")
                    st.write(f"**Keterangan:** {res['keterangan']}")
            response_msg = f"Menampilkan {len(final_results)} hasil untuk '{prompt}'"
        else:
            response_msg = "Maaf, data tidak ditemukan. Mohon gunakan kata kunci lain."
            st.warning(response_msg)

    st.session_state.messages.append({"role": "assistant", "content": response_msg})