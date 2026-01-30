import streamlit as st
import json
import os
import pandas as pd
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from thefuzz import fuzz
from datetime import datetime

# --------------------------------------------------
# 1. KONFIGURASI HALAMAN
# --------------------------------------------------
st.set_page_config(
    page_title="Klasifikasi Surat KPU",
    page_icon="📑",
    layout="centered"
)

# --------------------------------------------------
# 2. CUSTOM CSS (TIDAK DIUBAH)
# --------------------------------------------------
st.markdown("""
<style>
.stApp { background-color: white; color: #1e293b; }
.header-container {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 0;
    border-bottom: 1px solid #f1f5f9;
    margin-bottom: 50px;
}
.header-logo {
    background-color: #e11d48;
    color: white;
    padding: 8px;
    border-radius: 8px;
    font-weight: bold;
}
.header-text h1 {
    font-size: 1.1rem !important;
    margin: 0 !important;
}
.header-text p {
    font-size: 0.75rem;
    margin: 0;
    color: #64748b;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    flex-direction: row-reverse;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) 
[data-testid="stChatMessageContent"] {
    background-color: #2C2C2E !important;
    color: white !important;
    border-radius: 20px 5px 20px 20px !important;
    width: fit-content !important;
    margin-left: auto;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"])
[data-testid="stChatMessageContent"] {
    background-color: #f1f5f9 !important;
    border-radius: 5px 20px 20px 20px !important;
    border: 1px solid #e2e8f0;
}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# 3. NLP & DATABASE
# --------------------------------------------------
@st.cache_resource
def init_nlp():
    return StemmerFactory().create_stemmer()

@st.cache_data
def load_db():
    kode, jenis = [], []
    if os.path.exists("db_kode.json"):
        with open("db_kode.json", "r", encoding="utf-8") as f:
            kode = json.load(f)
    if os.path.exists("db_jenis.json"):
        with open("db_jenis.json", "r", encoding="utf-8") as f:
            jenis = json.load(f)
    return kode, jenis

stemmer = init_nlp()
db_kode, db_jenis = load_db()

# --------------------------------------------------
# 4. SMART SEARCH (TAMPILKAN SEMUA YANG MIRIP)
# --------------------------------------------------
def smart_search(query, db, stemmer, threshold=60):
    if not db:
        return []

    query_clean = query.lower().strip()
    query_stem = stemmer.stem(query_clean)
    results = []

    for item in db:
        teks = f"{item.get('klasifikasi','')} {item.get('keterangan','')}".lower()
        kode = item.get("kode", "").lower()

        score = fuzz.token_set_ratio(query_clean, teks)

        if query_clean == kode:
            score = 100
        elif query_clean in kode:
            score += 20

        if query_stem in teks:
            score += 10

        score = min(score, 100)

        if score >= threshold:
            temp = item.copy()
            temp["score"] = score
            results.append(temp)

    return sorted(results, key=lambda x: x["score"], reverse=True)

# --------------------------------------------------
# 5. MULTI SUGGESTION (INI KUNCI UTAMA)
# --------------------------------------------------
def suggest_corrections(query, db, threshold=70, limit=8):
    words = set()
    for item in db:
        teks = f"{item.get('klasifikasi','')} {item.get('keterangan','')}".lower()
        clean = "".join(c for c in teks if c.isalnum() or c.isspace())
        words.update(clean.split())

    suggestions = []
    for w in words:
        if len(w) < 4:
            continue
        score = fuzz.ratio(query.lower(), w)
        if threshold <= score < 100:
            suggestions.append((w, score))

    return sorted(suggestions, key=lambda x: x[1], reverse=True)[:limit]

# --------------------------------------------------
# 6. SESSION STATE
# --------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Halo! Silakan ketik kata kunci klasifikasi surat 📄"}
    ]

# --------------------------------------------------
# 7. HEADER
# --------------------------------------------------
st.markdown("""
<div class="header-container">
    <div class="header-logo">📄</div>
    <div class="header-text">
        <h1>Klasifikasi Surat KPU</h1>
        <p>Basis Data PKPU 1257</p>
    </div>
</div>
""", unsafe_allow_html=True)

# --------------------------------------------------
# 8. RENDER CHAT
# --------------------------------------------------
def render_results(results, title):
    if not results:
        return
    st.subheader(f"{title} ({len(results)} data)")
    for r in results:
        with st.expander(f"📍 {r.get('kode','-')} - {r.get('klasifikasi','')}"):
            st.markdown(f"**Relevansi:** {r['score']}%")
            st.write(f"**Sifat:** {r.get('sifat','-')}")
            st.info(r.get("keterangan","-"))

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "res_kode" in msg:
            render_results(msg["res_kode"], "🗂️ Kode Klasifikasi")
        if "res_jenis" in msg:
            render_results(msg["res_jenis"], "📄 Jenis Naskah")

# --------------------------------------------------
# 9. INPUT CHAT
# --------------------------------------------------
if prompt := st.chat_input("Ketik kata kunci..."):
    st.session_state.messages.append({"role": "user", "content": prompt})

    res_kode = smart_search(prompt, db_kode, stemmer)
    res_jenis = smart_search(prompt, db_jenis, stemmer)

    with st.chat_message("assistant"):
        if res_kode or res_jenis:
            st.markdown("Berikut semua data yang paling mirip:")
            render_results(res_kode, "🗂️ Kode Klasifikasi")
            render_results(res_jenis, "📄 Jenis Naskah")

            st.session_state.messages.append({
                "role": "assistant",
                "content": "Berikut hasil pencarian:",
                "res_kode": res_kode,
                "res_jenis": res_jenis
            })
        else:
            st.error(f"Tidak ditemukan data untuk **{prompt}**")

            suggestions = suggest_corrections(prompt, db_kode + db_jenis)

            if suggestions:
                st.markdown("💡 **Mungkin maksud Anda:**")
                for w, s in suggestions:
                    if st.button(f"🔍 {w} ({s}%)", key=f"s_{w}"):
                        st.session_state.messages.append(
                            {"role": "user", "content": w}
                        )
                        st.rerun()

            st.session_state.messages.append({
                "role": "assistant",
                "content": f"Tidak ditemukan hasil untuk '{prompt}'."
            })

    st.rerun()
