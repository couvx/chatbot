import streamlit as st
import json
import os
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from thefuzz import fuzz

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="DinasChat Pro", page_icon="🤖", layout="centered")

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
    except Exception as e:
        st.error(f"Gagal memuat database: {e}")
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
        # Pencarian Exact Match pada Kode
        if query_clean == kode: score += 100
        elif query_clean in kode: score += 60
        
        # Pencarian Berbasis Fuzzy (Kemiripan Teks)
        text_score = fuzz.token_set_ratio(query_clean, f"{klasifikasi} {keterangan}")
        stem_bonus = 15 if query_stemmed in (klasifikasi + keterangan) else 0
        
        final_score = min(score + text_score + stem_bonus, 100)
        
        # FILTER: Hanya tampilkan hasil dengan relevansi 75% ke atas
        if final_score >= 75:
            item_copy = item.copy()
            item_copy['score'] = final_score
            scored_results.append(item_copy)
            
    return sorted(scored_results, key=lambda x: x['score'], reverse=True)

# --- 3. INITIALIZATION ---
stemmer = init_nlp()
db_kode, db_jenis = load_db()

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Halo! Silakan tanya tentang **Kode Klasifikasi** atau **Jenis Surat**."}]

# --- 4. UI RENDERER ---
def render_results(results, title):
    if results:
        st.subheader(title)
        for r in results[:3]: 
            s = r.get('score', 0)
            # Warna indikator (Hijau jika sangat akurat)
            clr = "green" if s > 85 else "orange"
            with st.expander(f"📍 {r.get('kode', 'N/A')} - {r.get('klasifikasi', 'Detail')}"):
                st.markdown(f":{clr}[**Relevansi: {s}%**]")
                st.write(f"**Sifat:** {r.get('sifat', '-')}")
                st.info(f"**Keterangan:** {r.get('keterangan', '-')}")
        st.divider()

# --- 5. INTERFACE CHAT ---
st.title("🤖 DinasChat Pro")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "res_kode" in msg: render_results(msg["res_kode"], "🗂️ Hasil Kode Klasifikasi")
        if "res_jenis" in msg: render_results(msg["res_jenis"], "📄 Hasil Jenis Naskah")

if prompt := st.chat_input("Ketik kata kunci (misal: Kepegawaian)..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Lakukan pencarian
    res_kode = smart_search(prompt, db_kode, stemmer)
    res_jenis = smart_search(prompt, db_jenis, stemmer)

    with st.chat_message("assistant"):
        if res_kode or res_jenis:
            response_text = "Berikut adalah hasil yang paling relevan (75%-100%):"
            st.markdown(response_text)
            
            render_results(res_kode, "🗂️ Hasil Kode Klasifikasi")
            render_results(res_jenis, "📄 Hasil Jenis Naskah")
            
            st.session_state.messages.append({
                "role": "assistant", 
                "content": response_text,
                "res_kode": res_kode,
                "res_jenis": res_jenis
            })
        else:
            error_msg = f"Maaf, tidak ditemukan hasil dengan akurasi tinggi (75%+) untuk **'{prompt}'**. Coba gunakan kata kunci lain."
            st.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
    
    st.rerun()