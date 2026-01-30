import streamlit as st
import json
import os
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from thefuzz import fuzz

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Klasifikasi Surat KPU", page_icon="📄", layout="wide")

# Custom CSS untuk gaya KPU
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stChatMessage { border-radius: 15px; margin-bottom: 10px; }
    /* Menyesuaikan warna sidebar dan input */
    section[data-testid="stSidebar"] { background-color: white; border-right: 1px solid #eee; }
    .stChatInputContainer { padding-bottom: 30px; }
    /* Branding warna merah KPU */
    h1, h2, h3 { color: #d32f2f; }
    .stButton>button { width: 100%; border-radius: 10px; }
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
        # Ganti file sesuai database Anda
        if os.path.exists('db_kode.json'):
            with open('db_kode.json', 'r', encoding='utf-8') as f:
                kode_data = json.load(f)
        if os.path.exists('db_jenis.json'):
            with open('db_jenis.json', 'r', encoding='utf-8') as f:
                jenis_data = json.load(f)
        return kode_data, jenis_data
    except Exception as e:
        return [], []

def smart_search(query, db, stemmer):
    if not db: return []
    query_clean = query.lower().strip()
    query_stemmed = stemmer.stem(query_clean)
    scored_results = []
    
    for item in db:
        klasifikasi = item.get('klasifikasi', '').lower()
        keterangan = item.get('keterangan', '').lower()
        kode = item.get('kode', '').lower()
        
        score = 0
        if query_clean == kode: score += 100
        elif query_clean in kode: score += 60
        
        text_score = fuzz.token_set_ratio(query_clean, f"{klasifikasi} {keterangan}")
        stem_bonus = 15 if query_stemmed in (klasifikasi + keterangan) else 0
        
        final_score = min(score + text_score + stem_bonus, 100)
        
        if final_score >= 75:
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
    st.title("⚙️ Menu Utama")
    st.caption("PERCAKAPAN")
    st.button("💬 Chat Aktif", use_container_width=True, type="secondary")
    
    st.divider()
    
    # Fitur Tambahan di Sidebar
    if st.button("📥 Download Log Chat"):
        log_text = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
        st.download_button("Konfirmasi Download", log_text, file_name="log_chat_kpu.txt")
        
    if st.button("🗑️ Hapus Riwayat Chat", type="primary"):
        st.session_state.messages = []
        st.rerun()
    
    st.caption("Versi 1.1.0 - PKPU 1257")

# --- 5. UI RENDERER ---
def render_results(results, title):
    if results:
        st.markdown(f"**{title}**")
        for r in results[:3]: 
            s = r.get('score', 0)
            clr = "#2e7d32" if s > 85 else "#ed6c02"
            with st.expander(f"📍 {r.get('kode', 'N/A')} - {r.get('klasifikasi', 'Detail')}"):
                st.markdown(f"<span style='color:{clr}'>**Relevansi: {s}%**</span>", unsafe_allow_html=True)
                st.write(f"**Sifat:** {r.get('sifat', '-')}")
                st.info(f"**Keterangan:** {r.get('keterangan', '-')}")

# --- 6. MAIN INTERFACE ---
# Header Statis
col1, col2 = st.columns([0.1, 0.9])
with col1:
    st.image("https://upload.wikimedia.org/wikipedia/commons/4/46/KPU_Logo.svg", width=50) # Logo KPU
with col2:
    st.subheader("Klasifikasi Surat KPU")
    st.caption("Basis Data PKPU 1257")

# Tampilan jika chat kosong (Empty State)
if not st.session_state.messages:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
        st.markdown("<h1>📄</h1>", unsafe_allow_html=True)
        st.markdown("### **Klasifikasi Arsip KPU**", unsafe_allow_html=True)
        st.markdown("""
            Tanyakan Kode Klasifikasi dan Sifat Naskah  
            (Biasa/Rahasia) berdasarkan PKPU 1257. Silakan ketik  
            perihal surat Anda di bawah ini.
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# Menampilkan Riwayat Chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "res_kode" in msg: render_results(msg["res_kode"], "🗂️ Hasil Kode Klasifikasi")
        if "res_jenis" in msg: render_results(msg["res_jenis"], "📄 Hasil Jenis Naskah")

# Input Chat
if prompt := st.chat_input("Contoh: Kode dan sifat surat pelantikan KPPS..."):
    # Simpan pesan user
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Lakukan pencarian
    res_kode = smart_search(prompt, db_kode, stemmer)
    res_jenis = smart_search(prompt, db_jenis, stemmer)

    # Respon Assistant
    if res_kode or res_jenis:
        response_text = "Berikut adalah hasil klasifikasi berdasarkan PKPU 1257:"
        st.session_state.messages.append({
            "role": "assistant", 
            "content": response_text,
            "res_kode": res_kode,
            "res_jenis": res_jenis
        })
    else:
        error_msg = f"Maaf, tidak ditemukan hasil yang relevan untuk **'{prompt}'**. Pastikan kata kunci sesuai dengan istilah kearsipan."
        st.session_state.messages.append({"role": "assistant", "content": error_msg})
    
    st.rerun()

st.markdown("<div style='text-align: center; color: grey; font-size: 10px; margin-top: 50px;'>Hasil berdasarkan AI. Selalu verifikasi dengan dokumen fisik PKPU 1257.</div>", unsafe_allow_html=True)