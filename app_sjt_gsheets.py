import streamlit as st
import json
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- KONFIGURASI ---
PAGE_TITLE = "🎓 Survei Kompetensi Digital & Literasi AI Calon Guru"
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
        # Mengambil kredensial dari st.secrets (toml)
        secrets = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(secrets, scopes=SCOPE)
        client = gspread.authorize(creds)
        
        # Membuka Spreadsheet
        # Pastikan nama spreadsheet di Google Sheets sesuai dengan yang ada di secrets atau hardcoded
        sheet_url = st.secrets["spreadsheet"]["url"]
        sheet = client.open_by_url(sheet_url).sheet1
        return sheet
    except Exception as e:
        st.error(f"Gagal terkoneksi ke Google Sheets: {e}")
        return None

def save_to_gsheets(data_dict):
    """Menyimpan satu baris data ke Google Sheets"""
    sheet = connect_to_gsheets()
    if sheet:
        try:
            # Konversi dictionary ke list values sesuai urutan header
            # Kita ambil valuesnya saja, urutan harus konsisten
            values = list(data_dict.values())
            sheet.append_row(values)
            return True
        except Exception as e:
            st.error(f"Gagal menyimpan data: {e}")
            return False
    return False

# --- FUNGSI UTAMA ---
def load_questions():
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("File soal tidak ditemukan.")
        return []

def main():
    st.title(PAGE_TITLE)
    st.markdown("### Survei Kompetensi Digital & Literasi AI Calon Guru")
    
    # Cek apakah secrets sudah disetting
    if "gcp_service_account" not in st.secrets:
        st.warning("⚠️ Konfigurasi Google Sheets belum ditemukan. Aplikasi berjalan dalam Mode Demo (Data tidak tersimpan ke Cloud).")
        st.info("Silakan ikuti panduan di 'PANDUAN_DEPLOYMENT.md' untuk menghubungkan ke database.")

    with st.expander("📝 Data Responden", expanded=True):
        nama = st.text_input("Nama Lengkap")
        sekolah = st.text_input("Asal Universitas")
        pengalaman = st.selectbox("Semester/Tingkat ", ["< 5 Semester", "3-6", "> 6 Semester"])

    questions = load_questions()
    if not questions: return

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
            # Cek apakah semua soal sudah dijawab
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

                # 2. Siapkan Data
                data_payload = {
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Nama": nama,
                    "Sekolah": sekolah,
                    "Pengalaman": pengalaman,
                    "Total_Skor": total_score,
                }
                data_payload.update(details) # Gabungkan dengan detail jawaban

                # 3. Simpan
                success = False
                if "gcp_service_account" in st.secrets:
                    with st.spinner("Menyimpan ke Database Disertasi..."):
                        success = save_to_gsheets(data_payload)
                else:
                    st.warning("Mode Offline: Data hanya ditampilkan di layar.")
                    success = True # Bypass untuk demo

                if success:
                    st.success("✅ Data berhasil disimpan!")
                    st.metric("Skor Kompetensi", f"{total_score}")
                    st.balloons()

if __name__ == "__main__":
    main()
