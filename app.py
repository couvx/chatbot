import streamlit as st
import json
import os
import datetime
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from thefuzz import fuzz

# --- INITIALIZATION ---
def reset_chat():
    st.session_state.messages = []
    st.session_state.intent = None
    st.session_state.last_query = ""

if "messages" not in st.session_state:
    reset_chat()

# --- UI SIDEBAR ---
with st.sidebar:
    st.header("🛠️ Chat Controls")
    # Tombol Clear Chat
    if st.button("🗑️ Hapus Riwayat Chat", use_container_width=True):
        reset_chat()
        st.rerun()
    
    st.divider()
    st.info("Konteks Saat Ini: " + (st.session_state.intent if st.session_state.intent else "Umum"))

# --- LOGIKA PENCARIAN (REINFORCED) ---
def smart_search(query, db):
    # Validasi input agar tidak kosong
    if not query: return []
    
    query = query.lower()
    results = []
    
    for item in db:
        # Direct Code Search (Misal user ketik "PP.01")
        if query == item['kode'].lower():
            return [item]
        
        # Fuzzy Matching pada Klasifikasi & Keterangan
        content = f"{item['klasifikasi']} {item['keterangan']}".lower()
        score = fuzz.partial_ratio(query, content)
        
        if score > 75 or query in content:
            results.append(item)
            
    return results

# --- CHAT INTERFACE ---
st.title("🤖 Chatbot Naskah Dinas")

# Menampilkan chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Tanya kode atau jenis naskah..."):
    # Simpan pesan user
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 1. Intent Detection
    p_lower = prompt.lower()
    if any(x in p_lower for x in ["kode", "klasifikasi", "pp.", "pl.", "py."]):
        st.session_state.intent = "KODE"
    elif any(x in p_lower for x in ["jenis", "surat", "apa itu", "arti", "maksud"]):
        st.session_state.intent = "JENIS"

    # 2. Database Selection dengan Fallback
    # Jika intent terdeteksi, cari di DB tersebut. Jika tidak ketemu, cari di keduanya.
    load_k, load_j = load_db() # Fungsi load_db() dari kode sebelumnya
    
    if st.session_state.intent == "KODE":
        results = smart_search(prompt, load_k)
    elif st.session_state.intent == "JENIS":
        results = smart_search(prompt, load_j)
    else:
        # Pencarian Global jika intent tidak jelas
        results = smart_search(prompt, load_k) + smart_search(prompt, load_j)

    # 3. Response Rendering
    with st.chat_message("assistant"):
        if results:
            response_text = f"Berikut informasi yang saya temukan:"
            st.write(response_text)
            for res in results[:5]: # Tampilkan max 5 hasil
                with st.expander(f"📌 {res['kode']} - {res['klasifikasi']}"):
                    st.markdown(f"**Sifat:** `{res['sifat']}`")
                    st.markdown(f"**Keterangan:**\n{res['keterangan']}")
        else:
            response_text = "Maaf, saya tidak menemukan kode atau jenis tersebut. Coba gunakan kata kunci lain (misal: 'Anggaran' atau 'Nota')."
            st.warning(response_text)

    # Simpan pesan bot ke history
    st.session_state.messages.append({"role": "assistant", "content": response_text})