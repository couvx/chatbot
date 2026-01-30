import streamlit as st
import json
import datetime
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from thefuzz import fuzz

# --- INITIALIZATION ---
@st.cache_resource
def get_stemmer():
    return StemmerFactory().create_stemmer()

@st.cache_data
def load_databases():
    with open('db_kode.json', 'r', encoding='utf-8') as f:
        k = json.load(f)
    with open('db_jenis.json', 'r', encoding='utf-8') as f:
        j = json.load(f)
    return k, j

stemmer = get_stemmer()
db_kode, db_jenis = load_databases()

# --- SEARCH ENGINE ---
def search_in_db(query, db):
    query = query.lower().strip()
    results = []
    for item in db:
        # 1. Direct Match pada Kode
        if query == item['kode'].lower():
            return [item]
        
        # 2. Fuzzy Match pada Klasifikasi/Keterangan
        content = f"{item['klasifikasi']} {item['keterangan']}".lower()
        if query in content or fuzz.partial_ratio(query, content) > 85:
            results.append(item)
    return results

# --- UI STREAMLIT ---
st.title("🤖 Chatbot Naskah Dinas Terintegrasi")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar info
st.sidebar.header("Filter Database Aktif")

# --- MAIN LOGIC ---
if prompt := st.chat_input("Tanya Kode (ex: PP.01) atau Jenis (ex: Nota)..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # Pre-processing
    p_clean = prompt.lower()
    
    # 1. DETEKSI INTENT (Strict Separation)
    is_asking_kode = any(x in p_clean for x in ["kode", "klasifikasi", "nomor", "."])
    is_asking_jenis = any(x in p_clean for x in ["surat", "jenis", "naskah", "arti", "maksud"])

    results = []
    source_name = ""

    # 2. EKSEKUSI PENCARIAN (Hanya ke satu DB sesuai permintaan)
    if is_asking_kode:
        results = search_in_db(prompt, db_kode)
        source_name = "Database Kode/Klasifikasi"
    elif is_asking_jenis:
        results = search_in_db(prompt, db_jenis)
        source_name = "Database Jenis/Surat"
    else:
        # Jika user bertanya tanpa kata kunci spesifik, bot meminta klarifikasi
        response = "Mohon spesifikasikan apakah Anda bertanya tentang **Kode Klasifikasi** atau **Jenis Surat**?"
        with st.chat_message("assistant"):
            st.info(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.stop()

    # 3. TAMPILKAN HASIL
    with st.chat_message("assistant"):
        if results:
            st.success(f"Ditemukan di {source_name}:")
            for res in results[:5]:
                with st.expander(f"📌 {res['kode']} - {res['klasifikasi']}"):
                    st.write(f"**Sifat:** {res['sifat']}")
                    st.write(f"**Keterangan:** {res['keterangan']}")
            response_msg = f"Menampilkan {len(results)} hasil dari {source_name}."
        else:
            response_msg = f"Kata kunci tidak ditemukan di dalam {source_name}."
            st.warning(response_msg)
            
    st.session_state.messages.append({"role": "assistant", "content": response_msg})