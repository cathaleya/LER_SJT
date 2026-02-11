import streamlit as st
import json
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- KONFIGURASI ---
PAGE_TITLE = "🎓 Survei  AI TPACK"
DATA_FILE = "sjt_questions.json"
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

st.set_page_config(page_title=PAGE_TITLE, layout="centered")

# --- FUNGSI GOOGLE SHEETS ---
def connect_to_gsheets():
    """Mengkoneksikan ke Google Sheets menggunakan st.secrets"""
    try:
        secrets = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(secrets, scopes=SCOPE)
        client = gspread.authorize(creds)
        sheet_url = st.secrets["spreadsheet"]["url"]
        sheet = client.open_by_url(sheet_url).sheet1
        return sheet
    except Exception as e:
        return None # Silent error for now, handled in save/main

def save_to_gsheets(data_dict):
    """Menyimpan satu baris data ke Google Sheets"""
    sheet = connect_to_gsheets()
    if sheet:
        try:
            values = list(data_dict.values())
            sheet.append_row(values)
            return True
        except Exception as e:
            st.error(f"Gagal menyimpan data: {e}")
            return False
    else:
        st.error("Gagal terkoneksi ke Database. Pastikan Secrets sudah diatur.")
        return False

# --- FUNGSI UTAMA ---
def load_questions():
    """Memuat pertanyaan dari file JSON dengan penanganan encoding yang aman"""
    try:
        # Menggunakan utf-8-sig untuk menghandle BOM dari Windows
        with open(DATA_FILE, 'r', encoding='utf-8-sig') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"File '{DATA_FILE}' tidak ditemukan!")
        return []
    except json.JSONDecodeError as e:
        st.error(f"Error pada format file soal (JSON): {e}")
        return []

def main():
    st.title(PAGE_TITLE)
    st.markdown("### Survei Kompetensi Digital & Literasi AI Guru")
    
    # Cek Validasi Secrets
    if "gcp_service_account" not in st.secrets:
        st.warning("⚠️ Aplikasi belum terhubung ke Database.")
    
    with st.expander("📝 Data Responden", expanded=True):
        nama = st.text_input("Nama Lengkap")
        sekolah = st.text_input("Asal Universitas")

    questions = load_questions()
    if not questions:
        st.stop()

    with st.form("sjt_form"):
        answers = {}
        st.markdown("---")
        for q in questions:
            st.markdown(f"**Kasus: {q['dimensi']}**")
            st.info(q['skenario'])
            opsi_list = [f"A. {q['opsi']['A']}", f"B. {q['opsi']['B']}", f"C. {q['opsi']['C']}", f"D. {q['opsi']['D']}"]
            choice = st.radio(q['pertanyaan'], opsi_list, key=q['id'], index=None)
            if choice:
                answers[q['id']] = choice[0] # Ambil huruf A/B/C/D
            else:
                answers[q['id']] = None
            st.markdown("---")

        submitted = st.form_submit_button("Kirim Jawaban")

        if submitted:
            unanswered = [q['id'] for q in questions if answers[q['id']] is None]

            if not nama or not sekolah:
                st.error("Mohon lengkapi Data Responden (Nama dan Asal Sekolah).")
            elif unanswered:
                st.error(f"Mohon jawab semua pertanyaan. Belum dijawab: {', '.join(unanswered)}")
            else:
                # 1. Hitung Skor
                total_score = 0
                details = {}
                for q in questions:
                    sel = answers[q['id']]
                    poin = q['poin'][sel]
                    total_score += poin
                    details[f"{q['id']}_Jwb"] = sel
                    details[f"{q['id']}_Poin"] = poin

                # 2. Siapkan Payload
                data_payload = {
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Nama": nama,
                    "Sekolah": sekolah,
                    "Pengalaman": pengalaman,
                    "Total_Skor": total_score,
                }
                data_payload.update(details)

                # 3. Simpan
                if "gcp_service_account" in st.secrets:
                    with st.spinner("Menyimpan jawaban..."):
                        if save_to_gsheets(data_payload):
                            st.success("✅ Terima kasih! Jawaban Anda telah tersimpan.")
                            st.metric("Skor Kompetensi Anda", f"{total_score}")
                            st.balloons()
                else:
                    st.info("Mode Demo: Data tidak disimpan (Secrets belum diatur).")
                    st.metric("Skor Anda", f"{total_score}")

if __name__ == "__main__":
    main()

