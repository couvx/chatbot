import streamlit as st
import json
import os
import datetime
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from thefuzz import fuzz

# --- 1. DEFINISI FUNGSI (Harus di Atas) ---

@st.cache_resource
def init_nlp():
    """Inisialisasi Stemmer Bahasa Indonesia"""
    factory = StemmerFactory()
    return factory.create_stemmer()

@st.cache_data
def load_db():
    """Fungsi untuk memuat database JSON"""
    # Pastikan file ini ada di folder yang sama dengan app.py
    try:
        with open('db_kode.json', 'r', encoding='utf-8') as f:
            kode_db = json.load(f)
        with open('db_jenis.json', 'r', encoding='utf-8') as f:
            jenis_db = json.load(f)
        return kode_db, jenis_db
    except FileNotFoundError:
        st.error("File database (JSON) tidak ditemukan! Pastikan db_kode.json dan db_jenis.json tersedia.")
        return [], []

def write_log(query, intent, status):
    """Mencatat aktivitas chat ke file txt"""
    with open("chatbot_log.txt", "a", encoding="utf-8") as f:
        tgl = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{tgl}] Q: {query} | Intent: {intent} | Status: {status}\n")

def smart_search(query, db):
    """Logika pencarian dengan Fuzzy Matching & Direct Search"""
    query = query.lower().strip()
    if not query: return []
    
    results = []
    for item in db:
        # A. Direct Code Search (Prioritas Utama)
        if query == item['kode'].lower():
            return [item] # Langsung kembalikan jika kode persis
        
        # B. Fuzzy Matching pada Klasifikasi & Keterangan
        content = f"{item['klasifikasi']} {item['keterangan']}".lower()
        score = fuzz.partial_ratio(query, content)
        
        # Jika skor kemiripan > 75 atau kata kunci ada dalam teks
        if score > 75 or query in content:
            results.append(item)
            
    return results

# --- 2. CONFIG & STATE MANAGEMENT ---

st.set_page_config(page_title="DinasChat Pro", page_icon="🤖")

# Memanggil fungsi yang sudah didefinisikan di atas
stemmer = init_nlp()
db_kode, db_jenis = load_db()

if "messages" not in st.session_state:
    st.session_state.messages = []
if "intent" not in st.session_state:
    st.session_state.intent = None

# --- 3. UI SIDEBAR (Fitur Clear Chat & Auto-Update) ---

with st.sidebar:
    st.header("⚙️ Panel Kontrol")
    
    # Fitur Auto-Update
    if st.button("🔄 Auto-Update Database", use_container_width=True):
        st.cache_data.clear() # Menghapus cache agar baca ulang JSON
        st.success("Database diperbarui!")
        st.rerun()
        
    # Fitur Clear Chat
    if st.button("🗑️ Hapus Riwayat Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.intent = None
        st.rerun()
    
    st.divider()
    st.caption("Status Log: Aktif")
    if os.path.exists("chatbot_log.txt"):
        st.download_button("📥 Download Log", open("chatbot_log.txt", "rb"), "chat_log.txt")

# --- 4. INTERFACE CHAT ---

st.title("🤖 Chatbot Naskah Dinas")
st.markdown("Cari kode klasifikasi (ex: `PP.01`) atau jenis naskah (ex: `Laporan`).")

# Tampilkan history chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input User
if prompt := st.chat_input("Ketik pertanyaan Anda di sini..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # A. Intent Detection (State Management)
    p_clean = prompt.lower()
    if any(x in p_clean for x in ["kode", "klasifikasi", "pp.", "pl.", "py."]):
        st.session_state.intent = "KODE"
    elif any(x in p_clean for x in ["jenis", "surat", "apa itu", "arti", "maksud"]):
        st.session_state.intent = "JENIS"

    # B. Pencarian berdasarkan konteks
    if st.session_state.intent == "KODE":
        results = smart_search(prompt, db_kode)
    elif st.session_state.intent == "JENIS":
        results = smart_search(prompt, db_jenis)
    else:
        # Fallback: Cari di kedua DB jika intent tidak jelas
        results = smart_search(prompt, db_kode) + smart_search(prompt, db_jenis)

    # C. Menampilkan Jawaban
    with st.chat_message("assistant"):
        if results:
            header = "🔍 Hasil yang ditemukan:"
            st.write(header)
            for r in results[:5]: # Batasi 5 hasil agar tidak spam
                with st.expander(f"📍 {r['kode']} - {r['klasifikasi']}"):
                    st.write(f"**Sifat:** {r['sifat']}")
                    st.write(f"**Keterangan:** {r['keterangan']}")
            status_log = "Found"
        else:
            msg_error = "Maaf, informasi tidak ditemukan. Coba kata kunci lain."
            st.error(msg_error)
            status_log = "Not Found"

    # D. Logging
    write_log(prompt, st.session_state.intent, status_log)
    st.session_state.messages.append({"role": "assistant", "content": f"Sistem menemukan {len(results)} hasil."})