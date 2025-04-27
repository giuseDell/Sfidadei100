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
    if not df.empty and 'Data' in df.columns:
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
    return df

def save_series(data, esercizio, ripetizioni):
    df = load_data()
    oggi = datetime.date.today()

    if not df.empty and 'Data' in df.columns:
        serie_numero = len(df[(df['Data'].dt.date == oggi) & (df['Esercizio'] == esercizio)]) + 1
    else:
        serie_numero = 1

    new_row = [oggi.strftime('%Y-%m-%d'), esercizio, serie_numero, ripetizioni, '']
    worksheet.append_row(new_row)

def save_time_direct(tempo_minuti):
    oggi = datetime.date.today()
    records = worksheet.get_all_records()
    df = pd.DataFrame(records)
    if not df.empty and 'Data' in df.columns:
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
        if oggi in df['Data'].dt.date.values:
            idx = df[df['Data'].dt.date == oggi].index[0] + 2  # +2 per header
            worksheet.update_cell(idx, 5, tempo_minuti)
            return
    worksheet.append_row([oggi.strftime('%Y-%m-%d'), '', '', '', tempo_minuti])

# --- UI Streamlit ---
st.set_page_config(page_title="Sfida dei 100", page_icon="🏋️‍♂️", layout="wide")

st.image("logo_sfida100.png", width=150)
st.title("🏋️‍♂️ Sfida dei 100 - Pushup & Squat")

# Tabs
tabs = st.tabs(["Progressi", "Timer", "Allenamento Serie"])

# --- Progressi ---
with tabs[0]:
    st.header("🗓️ I tuoi progressi")
    df = load_data()

    start_date = datetime.date(2025, 4, 27)
    days = [start_date + datetime.timedelta(days=i) for i in range(90)]

    completati = df['Data'].dt.date.unique() if not df.empty else []

    # --- PRIMA creiamo tutti i bottoni per selezionare ---
    selected_day = None
    cols = st.columns(10)  # 10 colonne

    for i, day in enumerate(days):
        col = cols[i % 10]

        button_label = day.strftime('%d/%m')
        if col.button(button_label, key=f"giorno_{i}"):
            selected_day = day

    # --- DOPO assegniamo colori ai bottoni ---
    for i, day in enumerate(days):
        colore = "#222222"  # Nero base
        if day in completati:
            giorno_df = df[df['Data'].dt.date == day]
            pushup_tot = giorno_df[giorno_df['Esercizio'] == 'Pushup']['Ripetizioni'].sum()
            squat_tot = giorno_df[giorno_df['Esercizio'] == 'Squat']['Ripetizioni'].sum()
            if pushup_tot >= 100 and squat_tot >= 100:
                colore = "#00cc44"  # Verde completato
            else:
                colore = "#ffcc00"  # Giallo incompleto

        if selected_day == day:
            colore = "#3399ff"  # Azzurro se selezionato

        col = cols[i % 10]
        col.markdown(f"""
            <style>
            div[data-testid="stButton"][key="giorno_{i}"] > button {{
                background-color: {colore};
                color: white;
                height: 50px;
                width: 70px;
                border-radius: 10px;
                margin: 2px;
            }}
            </style>
        """, unsafe_allow_html=True)

    # --- Mostra Dettaglio se giorno selezionato ---
    if selected_day:
        giorno_df = df[df['Data'].dt.date == selected_day]
        tempo = giorno_df['Tempo Totale'].dropna().values
        tempo = tempo[0] if len(tempo) > 0 else 'Non registrato'

        st.subheader(f"Dettagli del {selected_day.strftime('%d/%m/%Y')}")
        st.metric("Tempo Totale (minuti)", tempo)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Pushup")
            pushup_df = giorno_df[giorno_df['Esercizio'] == 'Pushup'][['Serie', 'Ripetizioni']]
            if not pushup_df.empty:
                st.table(pushup_df)
            else:
                st.info("Nessuna serie di Pushup.")
        with col2:
            st.subheader("Squat")
            squat_df = giorno_df[giorno_df['Esercizio'] == 'Squat'][['Serie', 'Ripetizioni']]
            if not squat_df.empty:
                st.table(squat_df)
            else:
                st.info("Nessuna serie di Squat.")
                
# --- Timer ---
with tabs[1]:
    st.header("⏱️ Timer di Allenamento")

    if 'start_time' not in st.session_state:
        st.session_state.start_time = None
    if 'running' not in st.session_state:
        st.session_state.running = False

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Start"):
            st.session_state.start_time = time.time()
            st.session_state.running = True

    with col2:
        if st.button("Stop"):
            st.session_state.running = False
            if st.session_state.start_time is not None:
                elapsed_time = int(time.time() - st.session_state.start_time)
                minutes = elapsed_time // 60
                seconds = elapsed_time % 60
                save_time_direct(minutes)
                st.success(f"Tempo totale salvato: {minutes:02d}:{seconds:02d}")

    if st.session_state.running:
        elapsed_time = int(time.time() - st.session_state.start_time)
        minutes = elapsed_time // 60
        seconds = elapsed_time % 60
        st.metric(label="Tempo Allenamento", value=f"{minutes:02d}:{seconds:02d}")
        time.sleep(1)
        st.rerun()
        
# --- Allenamento Serie ---
with tabs[2]:
    st.header("🏆 Allenamento di oggi")

    oggi = datetime.date.today()
    df = load_data()

    if not df.empty and 'Data' in df.columns:
        df_today = df[df['Data'].dt.date == oggi]
    else:
        df_today = pd.DataFrame(columns=['Data', 'Esercizio', 'Serie', 'Ripetizioni', 'Tempo Totale'])

    pushup_tot = df_today[df_today['Esercizio'] == 'Pushup']['Ripetizioni'].sum()
    squat_tot = df_today[df_today['Esercizio'] == 'Squat']['Ripetizioni'].sum()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Pushup di oggi", f"{pushup_tot}/100")
    with col2:
        st.metric("Squat di oggi", f"{squat_tot}/100")

    st.divider()

    if 'aggiunto' not in st.session_state:
        st.session_state['aggiunto'] = False

    with st.form("aggiungi_serie"):
        esercizio = st.selectbox("Seleziona esercizio", ["Pushup", "Squat"])
        ripetizioni = st.number_input("Numero di ripetizioni", min_value=1, step=1)
        submitted = st.form_submit_button("Aggiungi Serie")

        if submitted:
            save_series(oggi, esercizio, ripetizioni)
            st.success(f"Serie aggiunta: {ripetizioni} {esercizio}")
            st.session_state['aggiunto'] = True
            st.rerun()

    if st.session_state.get('aggiunto', False):
        st.session_state['aggiunto'] = False
        st.rerun()

    st.subheader("Serie di oggi")
    if not df_today.empty:
        st.table(df_today[['Esercizio', 'Serie', 'Ripetizioni']].sort_values(by=['Esercizio', 'Serie']))

    if pushup_tot >= 100 and squat_tot >= 100:
        st.balloons()
        st.success("🎉 GIORNATA COMPLETATA! 100 PUSHUP E 100 SQUAT!")
