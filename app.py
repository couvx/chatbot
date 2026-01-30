import streamlit as st
import json
import os
import pandas as pd
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from thefuzz import fuzz
from datetime import datetime

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Klasifikasi Surat KPU", page_icon="📄", layout="wide")

# Custom CSS untuk UI sesuai gambar
st.markdown("""
    <style>
    /* Background Utama */
    .stApp { background-color: #f0f2f5; }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] { background-color: white; border-right: 1px solid #e0e0e0; }
    
    /* Chat Bubble User (Merah) */
    .user-bubble {
        background-color: #d32f2f;
        color: white;
        padding: 12px 18px;
        border-radius: 20px 20px 0px 20px;
        display: inline-block;
        max-width: 80%;
        float: right;
        margin: 5px 0;
    }
    
    /* Chat Bubble Assistant (Putih/Abu sangat muda) */
    .assistant-bubble {
        background-color: white;
        color: #333;
        padding: 15px 20px;
        border-radius: 0px 20px 20px 20px;
        display: inline-block;
        max-width: 90%;
        border: 1px solid #e0e0e0;
        margin: 5px 0;
        line-height: 1.6;
    }

    /* Avatar Container */
    .chat-row { display: flex; margin-bottom: 20px; width: 100%; }
    .row-reverse { flex-direction: row-reverse; }
    .avatar { width: 35px; height: 35px; border-radius: 50%; margin: 0 10px; }
    
    /* Welcome Screen */
    .welcome-container {
        display: flex; flex-direction: column; align-items: center;
        justify-content: center; text-align: center; padding: 60px 20px;
    }
    .welcome-icon { 
        background-color: #fff1f1; padding: 20px; border-radius: 20px;
        font-size: 40px; color: #d32f2f; margin-bottom: 20px; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CORE FUNCTIONS ---
@st.cache_resource
def init_nlp():
    return StemmerFactory().create_stemmer()

@st.cache_data
def load_db():
    kode_data, jenis_data = [], []
    try:
        if os.path.exists('db_kode.json'):
            with open('db_kode.json', 'r', encoding='utf-8') as f:
                kode_data = json.load(f)
        if os.path.exists('db_jenis.json'):
            with open('db_jenis.json', 'r', encoding='utf-8') as f:
                jenis_data = json.load(f)
        return kode_data, jenis_data
    except Exception:
        return [], []

def smart_search(query, db, stemmer):
    if not db: return []
    query_clean = query.lower().strip()
    query_stemmed = stemmer.stem(query_clean)
    scored_results = []
    
    for item in db:
        content = f"{item.get('klasifikasi', '')} {item.get('keterangan', '')}".lower()
        kode = item.get('kode', '').lower()
        score = 0
        if query_clean == kode: score += 100
        elif query_clean in kode: score += 60
        text_score = fuzz.token_set_ratio(query_clean, content)
        stem_bonus = 15 if query_stemmed in content else 0
        final_score = min(score + text_score + stem_bonus, 100)
        
        if final_score >= 75: # Tetap pada filter 75-100%
            item_copy = item.copy()
            item_copy['score'] = final_score
            scored_results.append(item_copy)
    return sorted(scored_results, key=lambda x: x['score'], reverse=True)

# --- 3. INITIALIZATION ---
stemmer = init_nlp()
db_kode, db_jenis = load_db()
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown("### 🏠 Menu Utama")
    st.write("---")
    st.caption("PERCAKAPAN")
    st.button("💬 Chat Aktif", use_container_width=True)
    
    st.write("") # Spacer
    
    if st.session_state.messages:
        chat_data = [{"Waktu": datetime.now().strftime("%H:%M"), "Role": m["role"], "Pesan": m["content"]} for m in st.session_state.messages]
        df_log = pd.DataFrame(chat_data)
        csv = df_log.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Log Chat", data=csv, file_name="log_chat_kpu.csv", use_container_width=True)
    
    if st.button("🗑️ Hapus Riwayat Chat", use_container_width=True, type="secondary"):
        st.session_state.messages = []
        st.rerun()
    
    st.markdown("<br><br><center><p style='font-size:10px; color:gray;'>Versi 1.1.0 - PKPU 1257</p></center>", unsafe_allow_html=True)

# --- 5. MAIN HEADER ---
col_logo, col_text = st.columns([0.07, 0.93])
with col_logo:
    st.image("https://upload.wikimedia.org/wikipedia/commons/4/46/KPU_Logo.svg", width=45)
with col_text:
    st.markdown("### **Klasifikasi Surat KPU**")
    st.caption("Basis Data PKPU 1257")

# --- 6. CHAT DISPLAY ---
if not st.session_state.messages:
    st.markdown(f"""
        <div class="welcome-container">
            <div class="welcome-icon">📄</div>
            <h2 style='color: #1a237e;'>Klasifikasi Arsip KPU</h2>
            <p style='color: #666;'>Tanyakan <b>**Kode Klasifikasi**</b> dan <b>**Sifat Naskah**</b><br>
            (Biasa/Rahasia) berdasarkan PKPU 1257. Silakan ketik<br>
            perihal surat Anda di bawah ini.</p>
        </div>
        """, unsafe_allow_html=True)
else:
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f"""
                <div class="chat-row row-reverse">
                    <img src="https://cdn-icons-png.flaticon.com/512/1144/1144760.png" class="avatar">
                    <div class="user-bubble">{msg['content']}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div class="chat-row">
                    <img src="https://cdn-icons-png.flaticon.com/512/2593/2593635.png" class="avatar">
                    <div class="assistant-bubble">
                        {msg['content']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            # Tampilkan Expander di bawah bubble asisten jika ada hasil
            if "res_kode" in msg:
                for r in msg["res_kode"][:3]:
                    with st.expander(f"📍 {r.get('kode')} - {r.get('klasifikasi')}"):
                        st.write(f"**Sifat:** {r.get('sifat')}")
                        st.info(f"**Keterangan:** {r.get('keterangan')}")

# --- 7. CHAT INPUT ---
if prompt := st.chat_input("Contoh: Kode dan sifat surat pelantikan KPPS..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    res_kode = smart_search(prompt, db_kode, stemmer)
    res_jenis = smart_search(prompt, db_jenis, stemmer)
    
    if res_kode or res_jenis:
        ans = "Tentu, berikut adalah hasil temuan saya berdasarkan **PKPU Nomor 1257**:"
        st.session_state.messages.append({
            "role": "assistant", "content": ans,
            "res_kode": res_kode, "res_jenis": res_jenis
        })
    else:
        st.session_state.messages.append({
            "role": "assistant", 
            "content": f"Maaf, saya tidak menemukan data dengan tingkat kecocokan di atas 75% untuk **'{prompt}'**."
        })
    st.rerun()

st.markdown("<br><center><p style='color: gray; font-size: 10px;'>Hasil berdasarkan AI. Selalu verifikasi dengan dokumen fisik PKPU 1257.</p></center>", unsafe_allow_html=True)