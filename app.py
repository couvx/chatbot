import streamlit as st
import json
import os
import datetime
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from thefuzz import fuzz

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="DinasChat Pro v2", page_icon="🤖", layout="centered")

# --- 2. CORE FUNCTIONS (NLP & SEARCH) ---

@st.cache_resource
def init_nlp():
    """Inisialisasi Stemmer Bahasa Indonesia"""
    return StemmerFactory().create_stemmer()

@st.cache_data
def load_db():
    """Memuat database JSON secara aman"""
    try:
        with open('db_kode.json', 'r', encoding='utf-8') as f:
            kode_db = json.load(f)
        with open('db_jenis.json', 'r', encoding='utf-8') as f:
            jenis_db = json.load(f)
        return kode_db, jenis_db
    except FileNotFoundError:
        return None, None

def detect_intent(prompt):
    """Smart Intent Detection menggunakan set intersection"""
    clean_prompt = "".join([c for c in prompt.lower() if c.isalnum() or c.isspace()])
    words = set(clean_prompt.split())
    
    keywords_kode = {"kode", "klasifikasi", "pp", "pl", "py", "nomor", "no"}
    keywords_jenis = {"jenis", "surat", "naskah", "maksud", "arti", "apa", "definisi"}

    if words.intersection(keywords_kode): return "KODE"
    if words.intersection(keywords_jenis): return "JENIS"
    return "GLOBAL"

def smart_search(query, db, stemmer):
    """Pencarian Cerdas dengan Scoring & Ranking"""
    if not db: return []
    
    query_clean = query.lower().strip()
    query_stemmed = stemmer.stem(query_clean)
    scored_results = []
    
    for item in db:
        content = f"{item['klasifikasi']} {item['keterangan']}".lower()
        
        # 1. Base Score menggunakan Token Set Ratio (handal untuk urutan kata acak)
        score = fuzz.token_set_ratio(query_clean, content)
        
        # 2. Bonus Score: Exact Code Match (Sangat Penting)
        if query_clean in item['kode'].lower():
            score += 40
            
        # 3. Bonus Score: Stemmed Keyword Match
        if query_stemmed in content:
            score += 15

        if score > 60: # Threshold minimal relevansi
            item_copy = item.copy()
            item_copy['score'] = min(score, 100) # Cap di 100%
            scored_results.append(item_copy)
            
    # Sorting berdasarkan skor tertinggi
    return sorted(scored_results, key=lambda x: x['score'], reverse=True)

def write_log(query, intent, status):
    with open("chatbot_log.txt", "a", encoding="utf-8") as f:
        tgl = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{tgl}] Q: {query} | Intent: {intent} | Status: {status}\n")

# --- 3. INITIALIZATION ---
stemmer = init_nlp()
db_kode, db_jenis = load_db()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Halo! Saya asisten naskah dinas Anda. Ada yang bisa saya bantu cari hari ini?"}
    ]

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("🤖 Control Panel")
    if st.button("🔄 Update Database", use_container_width=True):
        st.cache_data.clear()
        st.success("Database disegarkan!")
        st.rerun()
        
    if st.button("🗑️ Hapus Chat", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "content": "Riwayat dihapus. Silakan ajukan pertanyaan baru."}]
        st.rerun()

    st.divider()
    st.caption("Aplikasi ini menggunakan Fuzzy Logic & Stemming Sastrawi untuk akurasi pencarian.")

# --- 5. CHAT INTERFACE ---
st.title("🤖 DinasChat Pro")
st.markdown("Cari kode klasifikasi (Contoh: `PP.01`) atau jenis naskah (Contoh: `Surat Edaran`).")

# Render Riwayat Chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "results" in msg:
            for r in msg["results"]:
                label = "✅ Sangat Relevan" if r['score'] > 85 else "🔍 Relevan"
                color = "green" if r['score'] > 85 else "orange"
                with st.expander(f"📍 {r['kode']} - {r['klasifikasi']}"):
                    st.markdown(f":{color}[**{label}** ({r['score']}% match)]")
                    st.write(f"**Sifat:** {r['sifat']}")
                    st.info(f"**Keterangan:** {r['keterangan']}")

# Input User
if prompt := st.chat_input("Ketik di sini..."):
    # Tampilkan & Simpan Pesan User
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Logika Pencarian
    intent = detect_intent(prompt)
    if intent == "KODE":
        results = smart_search(prompt, db_kode, stemmer)
    elif intent == "JENIS":
        results = smart_search(prompt, db_jenis, stemmer)
    else:
        results = smart_search(prompt, db_kode, stemmer) + smart_search(prompt, db_jenis, stemmer)
        results = sorted(results, key=lambda x: x['score'], reverse=True)

    # Respon Assistant
    with st.chat_message("assistant"):
        if results:
            top_results = results[:5]
            response_text = f"Saya menemukan {len(results)} hasil. Berikut yang paling mendekati:"
            st.markdown(response_text)
            
            for r in top_results:
                label = "✅ Sangat Relevan" if r['score'] > 85 else "🔍 Relevan"
                color = "green" if r['score'] > 85 else "orange"
                with st.expander(f"📍 {r['kode']} - {r['klasifikasi']}"):
                    st.markdown(f":{color}[**{label}** ({r['score']}% match)]")
                    st.write(f"**Sifat:** {r['sifat']}")
                    st.info(f"**Keterangan:** {r['keterangan']}")
            
            st.session_state.messages.append({
                "role": "assistant", 
                "content": response_text,
                "results": top_results
            })
            status_log = "Found"
        else:
            error_msg = "Maaf, saya tidak menemukan data yang cocok. Cobalah kata kunci lain seperti 'Keuangan' atau 'Cuti'."
            st.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
            status_log = "Not Found"

    write_log(prompt, intent, status_log)
    st.rerun()