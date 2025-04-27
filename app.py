import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import datetime
import time

# --- Connessione a Google Sheets ---
creds = json.loads(st.secrets["GOOGLE_SHEETS_CREDENTIALS"])
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds, scope)
gc = gspread.authorize(credentials)

# ID del Google Sheets fornito
db_id = '1NEsc2hiWxnOvseH5YGktEdV39cmGyl0BzfNQoolfYAI'
spreadsheet = gc.open_by_key(db_id)
worksheet = spreadsheet.worksheet('DB')

# --- Funzioni Utili ---
def load_data():
    records = worksheet.get_all_records()
    df = pd.DataFrame(records)
    if not df.empty:
        df['Data'] = pd.to_datetime(df['Data'])
    return df

def save_series(data, esercizio, ripetizioni):
    df = load_data()
    oggi = datetime.date.today()
    serie_numero = len(df[(df['Data'] == pd.to_datetime(oggi)) & (df['Esercizio'] == esercizio)]) + 1
    new_row = [oggi.strftime('%Y-%m-%d'), esercizio, serie_numero, ripetizioni, '']
    worksheet.append_row(new_row)

def save_time(data, tempo_totale_minuti):
    df = load_data()
    oggi = datetime.date.today()
    righe_oggi = df[df['Data'] == pd.to_datetime(oggi)]
    if not righe_oggi.empty and pd.isna(righe_oggi.iloc[0]['Tempo Totale']):
        cella = worksheet.find(str(oggi.strftime('%Y-%m-%d')))
        worksheet.update_cell(cella.row, 5, f"{tempo_totale_minuti}")

# --- UI Streamlit ---
st.set_page_config(page_title="Sfida dei 100", page_icon="🏋️", layout="wide")

st.title("🏋️ Sfida dei 100 - Pushup & Squat")

# Tabs
tabs = st.tabs(["Progressi", "Timer", "Allenamento Serie"])

# --- Progressi ---
with tabs[0]:
    st.header("🗓️ I tuoi progressi")
    df = load_data()
    if df.empty:
        st.info("Nessun dato ancora registrato.")
    else:
        df['Data_only'] = df['Data'].dt.date
        giorni = sorted(df['Data_only'].unique())
        selected_day = st.selectbox("Seleziona un giorno", giorni[::-1])

        giorno_df = df[df['Data_only'] == selected_day]
        tempo = giorno_df['Tempo Totale'].dropna().values
        tempo = tempo[0] if len(tempo) > 0 else 'Non registrato'

        st.metric("Tempo Totale (minuti)", tempo)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Pushup")
            st.table(giorno_df[giorno_df['Esercizio'] == 'Pushup'][['Serie', 'Ripetizioni']])
        with col2:
            st.subheader("Squat")
            st.table(giorno_df[giorno_df['Esercizio'] == 'Squat'][['Serie', 'Ripetizioni']])

# --- Timer ---
with tabs[1]:
    st.header("🕰️ Timer di Allenamento")

    if 'start_time' not in st.session_state:
        st.session_state.start_time = None

    if st.button("Start Timer"):
        st.session_state.start_time = time.time()

    if st.button("Stop Timer"):
        if st.session_state.start_time is not None:
            elapsed_time = int((time.time() - st.session_state.start_time) / 60)  # minuti
            save_time(datetime.date.today(), elapsed_time)
            st.success(f"Allenamento registrato: {elapsed_time} minuti.")
            st.session_state.start_time = None
        else:
            st.warning("Timer non avviato!")

# --- Allenamento Serie ---
with tabs[2]:
    st.header("🏆 Allenamento di oggi")

    oggi = datetime.date.today()
    df = load_data()
    df_today = df[df['Data'] == pd.to_datetime(oggi)]

    pushup_tot = df_today[df_today['Esercizio'] == 'Pushup']['Ripetizioni'].sum()
    squat_tot = df_today[df_today['Esercizio'] == 'Squat']['Ripetizioni'].sum()

    st.metric("Pushup di oggi", f"{pushup_tot}/100")
    st.metric("Squat di oggi", f"{squat_tot}/100")

    st.divider()

    with st.form("aggiungi_serie"):
        esercizio = st.selectbox("Seleziona esercizio", ["Pushup", "Squat"])
        ripetizioni = st.number_input("Numero di ripetizioni", min_value=1, step=1)
        submitted = st.form_submit_button("Aggiungi Serie")

        if submitted:
            save_series(oggi, esercizio, ripetizioni)
            st.success(f"Serie aggiunta: {ripetizioni} {esercizio}")
            st.experimental_rerun()

    if pushup_tot >= 100 and squat_tot >= 100:
        st.success("🎉 Allenamento completato oggi! Ottimo lavoro!")

