import os
import json
from datetime import datetime

import streamlit as st
import pandas as pd
from thefuzz import fuzz
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory


# =========================================================
# 1. KONFIGURASI HALAMAN
# =========================================================
st.set_page_config(
    page_title="Klasifikasi Surat KPU",
    page_icon="📑",
    layout="centered"
)


# =========================================================
# 2. CUSTOM CSS (UI STYLING)
# =========================================================
st.markdown(
    """
    <style>
    /* ===== GLOBAL ===== */
    .stApp {
        background-color: white;
        color: #1e293b;
    }

    /* ===== HEADER ===== */
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
        color: #0f172a;
    }

    .header-text p {
        font-size: 0.75rem;
        margin: 0;
        color: #64748b;
    }

    /* ===== LANDING ===== */
    .landing-container {
        text-align: center;
        margin-top: 100px;
        margin-bottom: 50px;
    }

    .landing-icon {
        background-color: #fff1f2;
        color: #e11d48;
        width: 80px;
        height: 80px;
        line-height: 80px;
        border-radius: 50%;
        font-size: 40px;
        margin: 0 auto 24px;
    }

    /* ===== CHAT BUBBLE USER ===== */
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
        flex-direction: row-reverse;
        background-color: transparent !important;
    }

    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"])
    [data-testid="stChatMessageContent"] {
        background-color: #2C2C2E !important;
        color: white !important;
        border-radius: 20px 5px 20px 20px !important;
        padding: 10px 16px !important;
        width: fit-content !important;
        margin-left: auto;
    }

    /* ===== CHAT BUBBLE ASSISTANT ===== */
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"])
    [data-testid="stChatMessageContent"] {
        background-color: #f1f5f9 !important;
        color: #1e293b !important;
        border-radius: 5px 20px 20px 20px !important;
        padding: 12px 18px !important;
        border: 1px solid #e2e8f0;
    }

    [data-testid="stChatMessageAvatarAssistant"] {
        background-color: #64748b !important;
    }

    /* ===== SIDEBAR ===== */
    [data-testid="stSidebar"] {
        background-color: #f8f9fa;
        border-right: 1px solid #e0e0e0;
    }

    .sidebar-label {
        font-size: 0.75rem;
        font-weight: 800;
        color: #94a3b8;
        letter-spacing: 0.1rem;
        margin-bottom: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# 3. CORE FUNCTIONS
# =========================================================
@st.cache_resource
def init_nlp():
    """Inisialisasi stemmer Bahasa Indonesia"""
    return StemmerFactory().create_stemmer()


@st.cache_data
def load_db():
    """Load database JSON"""
    kode_data, jenis_data = [], []

    try:
        if os.path.exists("db_kode.json"):
            with open("db_kode.json", encoding="utf-8") as f:
                kode_data = json.load(f)

        if os.path.exists("db_jenis.json"):
            with open("db_jenis.json", encoding="utf-8") as f:
                jenis_data = json.load(f)

    except Exception as e:
        st.error(f"Gagal memuat database: {e}")

    return kode_data, jenis_data


def suggest_correction(query, db, threshold=70, limit=7):
    words_pool = set()

    for item in db:
        content = f"{item.get('klasifikasi', '')} {item.get('keterangan', '')}".lower()
        clean = "".join(c for c in content if c.isalnum() or c.isspace())
        words_pool.update(clean.split())

    suggestions = []
    for word in words_pool:
        if len(word) < 4:
            continue
        ratio = fuzz.ratio(query.lower(), word)
        if threshold <= ratio < 100:
            suggestions.append((word, ratio))

    # Urutkan dari paling mirip
    suggestions = sorted(suggestions, key=lambda x: x[1], reverse=True)

    return suggestions[:limit]


def smart_search(query, db, stemmer):
    """Pencarian cerdas dengan scoring"""
    if not db:
        return []

    query_clean = query.lower().strip()
    query_stem = stemmer.stem(query_clean)

    results = []

    for item in db:
        klasifikasi = item.get("klasifikasi", "").lower()
        keterangan = item.get("keterangan", "").lower()
        kode = item.get("kode", "").lower()

        score = 0
        if query_clean == kode:
            score += 100
        elif query_clean in kode:
            score += 60

        text_score = fuzz.token_set_ratio(
            query_clean, f"{klasifikasi} {keterangan}"
        )
        stem_bonus = 15 if query_stem in (klasifikasi + keterangan) else 0

        final_score = min(score + text_score + stem_bonus, 100)

        if final_score > 65:
            data = item.copy()
            data["score"] = final_score
            results.append(data)

    return sorted(results, key=lambda x: x["score"], reverse=True)


# =========================================================
# 4. INITIALIZATION
# =========================================================
stemmer = init_nlp()
db_kode, db_jenis = load_db()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Halo! Silakan tanya tentang **Kode Klasifikasi** atau **Jenis Surat**."
        }
    ]


# =========================================================
# 5. UI COMPONENTS
# =========================================================
def render_results(results, title):
    if not results:
        return

    st.subheader(title)

    for r in results[:3]:
        score = item.get("score", 0)
        color = "green" if score > 85 else "orange"

        with st.expander(
            f"📍 {item.get('kode', 'N/A')} - {item.get('klasifikasi', '-')}"
        ):
            st.markdown(f":{color}[**Relevansi: {score}%**]")
            st.write(f"**Sifat:** {item.get('sifat', '-')}")
            st.info(f"**Keterangan:** {item.get('keterangan', '-')}")


# =========================================================
# 6. SIDEBAR
# =========================================================
with st.sidebar:
    st.markdown('<div class="sidebar-label">PERCAKAPAN</div>', unsafe_allow_html=True)
    st.button("💬 Chat Aktif", use_container_width=True)

    st.markdown("<div style='height: 65vh'></div>", unsafe_allow_html=True)
    st.divider()

    if st.session_state.messages:
        df = pd.DataFrame(st.session_state.messages)
        st.download_button(
            "📥 Download Log Chat",
            df.to_csv(index=False).encode("utf-8"),
            "log_chat.csv",
            "text/csv",
            use_container_width=True
        )

    if st.button("🗑️ Hapus Riwayat Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# =========================================================
# 7. CHAT INTERFACE
# =========================================================
st.markdown(
    """
    <div class="header-container">
        <div class="header-logo">📄</div>
        <div class="header-text">
            <h1>Klasifikasi Surat KPU Basis Data PKPU 1257</h1>
            <p>Created by Nindya Rahma Wiranda</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "res_kode" in msg:
            render_results(msg["res_kode"], "🗂️ Hasil Kode Klasifikasi")
        if "res_jenis" in msg:
            render_results(msg["res_jenis"], "📄 Hasil Jenis Naskah")


# =========================================================
# 8. INPUT & LOGIC
# =========================================================
if prompt := st.chat_input("Ketik kata kunci (misal: Kepegawaian)..."):
    st.session_state.messages.append({"role": "user", "content": prompt})

    res_kode = smart_search(prompt, db_kode, stemmer)
    res_jenis = smart_search(prompt, db_jenis, stemmer)

    with st.chat_message("assistant"):
        if res_kode or res_jenis:
            st.markdown("Berikut adalah hasil temuan saya:")
            render_results(res_kode, "🗂️ Hasil Kode Klasifikasi")
            render_results(res_jenis, "📄 Hasil Jenis Naskah")

            st.session_state.messages.append({
                "role": "assistant",
                "content": "Berikut adalah hasil temuan saya:",
                "res_kode": res_kode,
                "res_jenis": res_jenis
            })
        else:
            error_msg = f"Maaf, tidak ditemukan data untuk **'{prompt}'**."
            st.error(error_msg)

            suggestions = suggest_correction(prompt, db_kode + db_jenis)
            if suggestions:
                st.markdown("💡 Mungkin maksud Anda adalah:")
                for word, score in suggestions:
                    if st.button(f"🔍 {word} ({score}%)", key=f"suggest_{word}"):
                        st.session_state.messages.append(
                            {"role": "user", "content": word}
                        )
                        st.rerun()

            st.session_state.messages.append(
                {"role": "assistant", "content": error_msg}
            )

    st.rerun()
