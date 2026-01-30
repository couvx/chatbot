import streamlit as st
import json
import os
import datetime
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from thefuzz import fuzz

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="DinasChat Pro", page_icon="🤖", layout="centered")

# --- 2. INISIALISASI RESOURCE (CACHE) ---

@st.cache_resource
def init_nlp():
    """Inisialisasi Stemmer Bahasa Indonesia"""
    factory = StemmerFactory()
    return factory.create_stemmer()

@st.cache_data
def load_db():
    """Fungsi untuk memuat database JSON"""
    try:
        # Load database kode klasifikasi
        with open('db_kode.json', 'r', encoding='utf-8') as f:
            kode_db = json.load(f)
        # Load database jenis naskah
        with open('db_jenis.json', 'r', encoding='utf-8') as f:
            jenis_db = json.load(f)
        return kode_db, jenis_db
    except FileNotFoundError:
        return None, None

# Inisialisasi awal
stemmer = init_nlp()
db_kode, db_jenis = load_db()

# --- 3. FUNGSI LOGIKA (BACKEND) ---

def write_log(query, intent, status):
    """Mencatat aktivitas chat ke file txt"""
    with open("chatbot_log.txt", "a", encoding="utf-8") as f:
        tgl = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{tgl}] Q: {query} | Intent: {intent} | Status: {status}\n")

def detect_intent(prompt):
    """NLP Sederhana: Deteksi niat user menggunakan pembersihan teks & set intersection"""
    # Bersihkan teks: kecilkan huruf dan hapus tanda baca
    clean_prompt = "".join([c for c in prompt.lower() if c.isalnum() or c.isspace()])
    words = set(clean_prompt.split())
    
    # Kamus kata kunci (bisa ditambah sesuai kebutuhan)
    keywords_kode = {"kode", "klasifikasi", "pp", "pl", "py", "nomor", "no", "katalog"}
    keywords_jenis = {"jenis", "surat", "naskah", "maksud", "arti", "definisi", "apa", "pengertian", "penjelasan"}

    # Logika deteksi
    if words.intersection(keywords_kode):
        return "KODE"
    elif words.intersection(keywords_jenis):
        return "JENIS"
    return "UNKNOWN"

def smart_search(query, db):
    """Logika pencarian dengan Fuzzy Matching & Stemming"""
    if not db: return []
    
    query_clean = query.lower().strip()
    query_stemmed = stemmer.stem(query_clean)
    results = []
    
    for item in db:
        # A. Direct Code Search (Prioritas Utama)
        if query_clean == item['kode'].lower():
            return [item] 
        
        # B. Fuzzy Matching & Keyword Search
        content = f"{item['klasifikasi']} {item['keterangan']}".lower()
        score = fuzz.partial_ratio(query_clean, content)
        
        # Cek apakah query ada di konten (atau versi stem-nya)
        if score > 75 or query_clean in content or query_stemmed in content:
            results.append(item)
            
    return results

# --- 4. STATE MANAGEMENT ---

if "messages" not in st.session_state:
    st.session_state.messages = []
    # Pesan sambutan pertama kali
    st.session_state.messages.append({"role": "assistant", "content": "Halo! Silakan tanya mengenai Kode Klasifikasi atau Jenis Naskah Dinas."})

# --- 5. UI SIDEBAR ---

with st.sidebar:
    st.header("⚙️ Panel Kontrol")
    
    if st.button("🔄 Refresh Database", use_container_width=True):
        st.cache_data.clear()
        st.success("Database diperbarui!")
        st.rerun()
        
    if st.button("🗑️ Hapus Riwayat Chat", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "content": "Riwayat dihapus. Ada yang bisa saya bantu?"}]
        st.rerun()
    
    st.divider()
    if os.path.exists("chatbot_log.txt"):
        st.download_button("📥 Download Log Aktivitas", open("chatbot_log.txt", "rb"), "chat_log.txt")

# --- 6. INTERFACE CHAT ---

st.title("🤖 DinasChat Pro")
st.caption("Sistem Informasi Naskah Dinas Otomatis")

# Render Riwayat Chat (Ini yang membuat chat tidak hilang)
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        # Jika ada data hasil pencarian di pesan assistant sebelumnya, tampilkan ulang (opsional)
        if "results" in msg:
            for r in msg["results"]:
                with st.expander(f"📍 {r['kode']} - {r['klasifikasi']}"):
                    st.write(f"**Sifat:** {r['sifat']}")
                    st.write(f"**Keterangan:** {r['keterangan']}")

# Input Chat
if prompt := st.chat_input("Contoh: Apa itu surat edaran? / Cari kode PP.01"):
    
    # 1. Simpan & Tampilkan Pesan User
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Deteksi Intent & Cari Data
    intent = detect_intent(prompt)
    
    if intent == "KODE":
        results = smart_search(prompt, db_kode)
    elif intent == "JENIS":
        results = smart_search(prompt, db_jenis)
    else:
        # Gabungkan hasil jika intent tidak spesifik
        results = smart_search(prompt, db_kode) + smart_search(prompt, db_jenis)

    # 3. Respon Assistant
    with st.chat_message("assistant"):
        if results:
            msg_text = f"Ditemukan {len(results)} informasi terkait pertanyaan Anda:"
            st.markdown(msg_text)
            
            # Batasi tampilan agar tidak memenuhi layar
            display_results = results[:5]
            for r in display_results:
                with st.expander(f"📍 {r['kode']} - {r['klasifikasi']}"):
                    st.write(f"**Sifat:** {r['sifat']}")
                    st.write(f"**Keterangan:** {r['keterangan']}")
            
            # Simpan ke session state
            st.session_state.messages.append({
                "role": "assistant", 
                "content": msg_text,
                "results": display_results # Simpan data hasil agar tetap ada saat rerun
            })
            status_log = "Found"
        else:
            error_msg = "Maaf, saya tidak menemukan data yang cocok. Coba gunakan kata kunci lain seperti 'Surat Perintah' atau kode 'PL'."
            st.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
            status_log = "Not Found"

    # 4. Finalisasi
    write_log(prompt, intent, status_log)
    st.rerun() # Memicu refresh agar UI sinkron