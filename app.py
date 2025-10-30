import streamlit as st # type: ignore
import pandas as pd # type: ignore
import plotly.express as px # type: ignore
import gspread # type: ignore
import numpy as np # type: ignore
import math 

# PENGATURAN PAGE CONFIG
st.set_page_config(layout="wide")

# ------------------------------------------------------------------
# --- INISIALISASI SESSION STATE ---
if 'active_tab_name' not in st.session_state:
    st.session_state.active_tab_name = "Hub Tracker" 

def set_active_tab(tab_name):
    st.session_state.active_tab_name = tab_name

# ------------------------------------------------------------------
# --- CSS FINAL: Hanya untuk Layout dan DataFrame ---
st.markdown("""
    <style>
    /* 1. Pengaturan Layout Dasar */
    .main { overflow-y: hidden; }
    [data-testid="stSidebar"] { overflow-y: hidden; }
    div[data-testid="stDataFrame"] { overflow-y: hidden !important; }
    div[role="tablist"] { display: flex; justify-content: center; }
    /* Menghilangkan nomor indeks DataFrame */
    [data-testid="stDataFrame"] .row-data-viewer-container > div:first-child { display: none !important; }
    </style>
""", unsafe_allow_html=True)
# ------------------------------------------------------------------


st.title("TRACKER NEEDS LAMPUNG")


# --- KONFIGURASI SUMBER DATA AMAN (SERVICE ACCOUNT) ---
GSHEET_ID = "1a2zsxpZjc4hO2AZEWj_Ut0xcHa1RLFhOdAWfwBgr8Ak" 
GSHEET_GID = "606760587"

# --- DEFINISI KOLOM KITA ---
FINAL_COLUMNS = [
    'HUB_NAME', 'CITY_FILTER', 'CITY', 
    'RD', 'RM', 'DD', 'DM', 
    'CRM', 'CDM', 
    'GAP_TOTAL', 'PIC_BPOM', 
    'NOTES' 
]

# --- URUTAN KOLOM YANG DIMINTA UNTUK DITAMPILKAN ---
DISPLAY_COLUMNS_ORDER = [
    'HUB_NAME', 'CITY', 
    'RD', 'RM', 'DD', 'DM', 'CRM', 'CDM', 
    'GAP_TOTAL', 
    'PIC_BPOM',
    'NOTES' 
]

# --- FUNGSI UTAMA: MEMBACA DARI GOOGLE SHEET AMAN ---
@st.cache_data(ttl=600)
def load_and_merge_data_secure(sheet_id, sheet_gid):
    try:
        # Pengecekan service account dan loading data
        gc = gspread.service_account_from_dict(st.secrets["gspread"])
        sh = gc.open_by_key(sheet_id)
        worksheet = sh.get_worksheet_by_id(int(sheet_gid)) 
        
        # --- LANGKAH BARU: Mengambil nilai dari sel Y1 untuk Last Update ---
        last_update_value = worksheet.acell('Y1').value
        # -----------------------------------------------------------------
        
        list_of_lists = worksheet.get_all_values()
        
        df_raw = pd.DataFrame(list_of_lists)
        
        if len(df_raw) <= 6:
            st.error("Data Sheet terlalu pendek.")
            return pd.DataFrame(), last_update_value # Mengembalikan DataFrame kosong dan Update Value

        df_raw.columns = df_raw.iloc[5] 
        df_data = df_raw.iloc[6:].reset_index(drop=True) 
        df_data = df_data.dropna(how='all')
        
        df_id = df_data.iloc[:, [0, 2, 3]].copy() 
        df_id.columns = FINAL_COLUMNS[0:3] 

        df_gap_info = df_data.iloc[:, 16:24].copy() 
        df_gap_info.columns = FINAL_COLUMNS[3:11]

        df_notes = df_data.iloc[:, [24]].copy() 
        df_notes.columns = [FINAL_COLUMNS[11]] 
        
        df_temp = pd.concat([df_id, df_gap_info, df_notes], axis=1) 

        df_final = df_temp[df_temp['CITY_FILTER'].str.upper() == 'LAMPUNG'].copy()

        df_final = df_final.dropna(subset=['HUB_NAME']).reset_index(drop=True)
        df_final = df_final.drop(columns=['CITY_FILTER'])

        gap_cols_to_convert = ['RD', 'RM', 'DD', 'DM', 'CRM', 'CDM', 'GAP_TOTAL'] 
        
        for col in gap_cols_to_convert:
            df_final[col] = df_final[col].astype(str).str.replace(',', '.', regex=False)
            df_final[col] = pd.to_numeric(df_final[col], errors='coerce').fillna(0).astype(int)
            
        return df_final, last_update_value # Mengembalikan DataFrame dan Update Value
        
    except Exception as e:
        if "gspread" in str(e):
            st.error("🚨 Kesalahan Otentikasi/Akses Google Sheet. Pastikan secrets.toml dan izin sudah benar.")
        else:
            st.error(f"❌ Gagal memuat data. Error: {e}")
        return pd.DataFrame(), "Gagal Mengambil" # Mengembalikan DataFrame kosong dan notifikasi error

# --- BAGIAN UTAMA: MEMUAT DATA & MENAMPILKAN UPDATE ---
# PENTING: Fungsi sekarang mengembalikan dua nilai
df_clean, last_update = load_and_merge_data_secure(GSHEET_ID, GSHEET_GID)

# --- MENAMPILKAN INFORMASI UPDATE TERAKHIR ---
if last_update and last_update != "Gagal Mengambil":
    st.info(f"**{last_update}**")

# MENGGUNAKAN LOGIKA AKTIF TAB BERDASARKAN SESSION STATE
tab_names = ["Hub Tracker", "Global View"]

tab1_obj, tab2_obj = st.tabs(
    tab_names, 
)

# =====================================================================
# --- TAB 1: HUB TRACKER ---
# =====================================================================
with tab1_obj:
    
    if not df_clean.empty:
        
        # --- KONFIGURASI DATAFRAME BARU ---
        # CATATAN: Format angka masih menggunakan .style.format (memungkinkan bug Streamlit)
        dataframe_config = {
            "HUB_NAME": st.column_config.Column(
                label="Nama Hub", 
                width=200, 
            ),
            "CITY": st.column_config.Column(
                label="Kab/Kota", 
                width=200, 
            ),
            "NOTES": st.column_config.Column(
                width="large",
                disabled=True,
            )
        }
        
        df_display_base = df_clean[DISPLAY_COLUMNS_ORDER]
        # Baris ini berpotensi menyebabkan bug format angka di Streamlit
        df_display_base_styled = df_display_base.style.format({
            col: "{:,}" for col in ['GAP_TOTAL', 'RD', 'RM', 'DD', 'DM', 'CRM', 'CDM']
        })
        
        # Tinggi Dinamis untuk DataFrame
        ROW_HEIGHT_PX = 35 
        HEADER_HEIGHT_PX = 35
        MAX_HEIGHT_PX = 600
        
        required_height_base = (len(df_display_base) * ROW_HEIGHT_PX) + HEADER_HEIGHT_PX
        final_height_base = min(required_height_base, MAX_HEIGHT_PX)

        # --- DATAFRAME UTAMA (GLOBAL VIEW) ---
        st.header("All Hubs Lampung")
        st.dataframe(
            df_display_base_styled, 
            use_container_width=True, 
            height=final_height_base, 
            column_config=dataframe_config 
        )
        
    else:
        st.warning("Dataframe kosong. Silakan periksa sumber data atau filter 'LAMPUNG'.") 


# =====================================================================
# --- TAB 2: GLOBAL VIEW ---
# =====================================================================
with tab2_obj:
    
    if not df_clean.empty:
        
        # ------------------------------------------------------------------
        # --- VISUALISASI 1: GLOBAL GAP (TOTAL per CITY) ---
        # ------------------------------------------------------------------
        st.header("📈 Global View")
        
        df_city_gap_chart = df_clean.groupby('CITY')['GAP_TOTAL'].sum().reset_index() 
        df_city_gap_chart['GAP_TOTAL'] = pd.to_numeric(df_city_gap_chart['GAP_TOTAL'], errors='coerce')
        df_city_gap_chart = df_city_gap_chart.sort_values(by='GAP_TOTAL', ascending=False)
        
        max_gap_value = df_city_gap_chart['GAP_TOTAL'].max()
        y_axis_range_max = max_gap_value * 1.10
        
        df_city_gap_chart['GAP_LABEL'] = df_city_gap_chart['GAP_TOTAL'].apply(lambda x: f'{x:,}')
        
        fig1 = px.bar(
            df_city_gap_chart,
            x='CITY',
            y='GAP_TOTAL',
            title='Total GAP Berdasarkan Kab/Kota',
            labels={'GAP_TOTAL': 'Total GAP', 'CITY': 'Kota'},
            color='GAP_TOTAL', 
            color_continuous_scale=px.colors.sequential.Bluered,
            text='GAP_LABEL',
            hover_data={'CITY': True, 'GAP_TOTAL': ':,', 'GAP_LABEL': False} 
        )
        
        fig1.update_traces(
            texttemplate='%{text}', 
            textposition='outside',
            customdata=df_city_gap_chart[['CITY', 'GAP_TOTAL']].apply(
                lambda x: [x['CITY'], f"{x['GAP_TOTAL']:,}"], axis=1
            )
        )
        
        fig1.update_layout(
            xaxis={'categoryorder':'array', 'categoryarray': df_city_gap_chart['CITY']}, 
            xaxis_title='Kota',
            yaxis_title='Total GAP',
            height=600, 
            yaxis_visible=True, 
            yaxis_showticklabels=True,
            yaxis=dict(
                range=[0, y_axis_range_max]
            ),
            coloraxis_showscale=False
        )
        st.plotly_chart(fig1, use_container_width=True)

        # ------------------------------------------------------------------
        # --- VISUALISASI 2: DETAIL GAP (GLOBAL - Tanpa Filter Kota) ---
        # ------------------------------------------------------------------
        st.header("🔍 Gap Needs - Posisi")

        # Hitung komposisi GAP total untuk semua kota di Lampung
        GAP_COMPONENTS = ['RD', 'RM', 'DD', 'DM', 'CRM', 'CDM']
        df_detail = df_clean[GAP_COMPONENTS].sum().reset_index()
        df_detail.columns = ['Tipe_GAP', 'Total_GAP']
        df_detail = df_detail.sort_values(by='Total_GAP', ascending=False)
        df_detail['GAP_LABEL'] = df_detail['Total_GAP'].apply(lambda x: f'{x:,}')

        # Buat Bar Chart Detail
        fig2 = px.bar(
            df_detail,
            x='Tipe_GAP',
            y='Total_GAP',
            title='Komposisi Total GAP Berdasarkan Posisi',
            labels={'Total_GAP': 'Total GAP', 'Tipe_GAP': 'Tipe GAP'},
            color='Total_GAP', 
            color_continuous_scale=px.colors.sequential.Teal,
            text='GAP_LABEL',
            hover_data={'Tipe_GAP': True, 'Total_GAP': ':,', 'GAP_LABEL': False} 
        )
        
        fig2.update_traces(
            texttemplate='%{text}', 
            textposition='outside'
        )
        
        fig2.update_layout(
            xaxis_title='Posisi',
            yaxis_title='Jumlah GAP',
            height=500,
            coloraxis_showscale=False
        )
        st.plotly_chart(fig2, use_container_width=True)
            
    else:
        st.warning("""
            Dataframe kosong. Silakan periksa Service Account, secrets.toml, atau izin akses Google Sheet.

        """)

