import streamlit as st
import pandas as pd
from fitparse import FitFile
import tempfile
import os
import io
import zipfile
from datetime import datetime

st.set_page_config(page_title="FIT Converter", layout="wide", initial_sidebar_state="expanded")
st.title("🚴‍♂️ FIT ➡️ CSV (Mobile Friendly & Zip Support)")
st.write("Estrai dati da file .fit o .zip - Ottimizzato per PC, Pixel e iOS")

# ═══════════════════════════════════════════════════════════════
# CONFIGURAZIONE SIDEBAR
# ═══════════════════════════════════════════════════════════════
st.sidebar.header("⚙️ Opzioni")
extract_mode = st.sidebar.radio(
    "Modalità estrazione:",
    ["Records (Dati continui)", "Tutti i messaggi", "Records + Statistiche"],
    help="Scegli cosa estrarre dal file FIT"
)

# ═══════════════════════════════════════════════════════════════
# FILE UPLOADER (Senza filtri type per garantire compatibilità Android)
# ═══════════════════════════════════════════════════════════════
st.write("### 📥 Carica un file .fit o .zip")
uploaded_file = st.file_uploader(
    "Trascina o seleziona un file .fit o un archivio .zip",
    help="Supporta file singoli .fit o archivi .zip contenenti file FIT"
)

if uploaded_file is not None:
    file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
    
    if file_size_mb > 50:
        st.error(f"❌ File troppo grande ({file_size_mb:.1f} MB)")
        st.stop()
        
    st.info(f"📊 Analisi in corso... ({file_size_mb:.1f} MB)")
    
    tmp_path = None
    fit_data = uploaded_file.getvalue()
    df = pd.DataFrame()
    
    try:
        # Gestione file ZIP
        if uploaded_file.name.lower().endswith('.zip'):
            st.write("🔍 Estrazione archivio zip...")
            with tempfile.TemporaryDirectory() as extract_dir:
                with zipfile.ZipFile(io.BytesIO(fit_data)) as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                fit_files = []
                for root, dirs, files in os.walk(extract_dir):
                    for file in files:
                        if file.lower().endswith('.fit'):
                            fit_files.append(os.path.join(root, file))
                
                if not fit_files:
                    st.error("❌ Nessun file .fit trovato all'interno dello zip!")
                    st.stop()
                
                # Prende il primo file FIT trovato
                with open(fit_files[0], 'rb') as f:
                    fit_data = f.read()
                st.success(f"✅ Estratto con successo: {os.path.basename(fit_files[0])}")

        # Creazione file temporaneo sicuro per fitparse
        with tempfile.NamedTemporaryFile(delete=False, suffix=".fit") as tmp:
            tmp.write(fit_data)
            tmp_path = tmp.name
            
        fitfile = FitFile(tmp_path)
        
        # ═══════════════════════════════════════════════════════════════
        # ESTRAZIONE DATI IN BASE ALLA MODALITÀ SÉLEZIONATA
        # ═══════════════════════════════════════════════════════════════
        
        if extract_mode in ["Records (Dati continui)", "Records + Statistiche"]:
            records = []
            for record in fitfile.get_messages('record'):
                record_data = {}
                for data in record:
                    value = data.value
                    if isinstance(value, (list, tuple)):
                        value = str(value)
                    # I valori mancanti (None) NON vengono convertiti in stringhe vuote
                    # per permettere a Pandas di riconoscerli come numeri (NaN)
                    record_data[data.name] = value
                records.append(record_data)
                
            if records:
                df = pd.DataFrame(records)
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', errors='coerce')
                
                st.success(f"✅ {len(df)} record continui estratti con successo")
                
                # Se la modalità include le statistiche avanzate, mostra i KPI in alto
                if extract_mode == "Records + Statistiche":
                    kpi = st.columns(5)
                    with kpi[0]:
                        st.metric("Punti Registrati", len(df))
                    with kpi[1]:
                        if 'timestamp' in df.columns and not df['timestamp'].isnull().all():
                            duration = df['timestamp'].max() - df['timestamp'].min()
                            st.metric("Durata Attività", str(duration).split('.')[0])
                    with kpi[2]:
                        if 'distance' in df.columns:
                            dist = pd.to_numeric(df['distance'], errors='coerce').max() / 1000
                            st.metric("Distanza", f"{dist:.2f} km" if not pd.isnull(dist) else "N/A")
                    with kpi[3]:
                        if 'heart_rate' in df.columns:
                            avg_hr = pd.to_numeric(df['heart_rate'], errors='coerce').mean()
                            st.metric("FC Media", f"{avg_hr:.0f} bpm" if not pd.isnull(avg_hr) else "N/A")
                    with kpi[4]:
                        if 'power' in df.columns:
                            avg_pwr = pd.to_numeric(df['power'], errors='coerce').mean()
                            st.metric("Potenza Media", f"{avg_pwr:.0f} watt" if not pd.isnull(avg_pwr) else "N/A")
                
                st.write("### 📋 Anteprima della tabella dati:")
                st.dataframe(df.head(10), use_container_width=True)
                
                # Statistiche matematiche sui campi numerici puri
                numeric_cols = df.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0 and extract_mode == "Records (Dati continui)":
                    st.write("### 📊 Riepilogo statistico dei campi numerici:")
                    st.dataframe(df[numeric_cols].describe(), use_container_width=True)
            else:
                st.warning("⚠️ Nessun record continuo ('record') trovato in questo file.")
                
        elif extract_mode == "Tutti i messaggi":
            all_messages = {}
            for message in fitfile.get_messages():
                msg_type = message.name
                if msg_type not in all_messages:
                    all_messages[msg_type] = []
                
                msg_data = {}
                for data in message:
                    value = data.value
                    if isinstance(value, (list, tuple)):
                        value = str(value)
                    msg_data[data.name] = value
                all_messages[msg_type].append(msg_data)
                
            st.success(f"✅ Trovati {len(all_messages)} tipi di messaggi differenti nel file")
            
            st.write("### 📝 Riepilogo dei messaggi disponibili:")
            for msg, msgs in all_messages.items():
                st.write(f"  • **{msg}**: {len(msgs)} righe presenti")
                
            selected_msg = st.selectbox("Seleziona quale tipo di messaggio vuoi ispezionare ed esportare:", list(all_messages.keys()))
            df = pd.DataFrame(all_messages[selected_msg])
            
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', errors='coerce')
                
            st.dataframe(df.head(10), use_container_width=True)

        # ═══════════════════════════════════════════════════════════════
        # GENERAZIONE EXPORT (CSV / EXCEL)
        # ═══════════════════════════════════════════════════════════════
        if not df.empty:
            st.divider()
            st.write("### 💾 Scarica i dati convertiti:")
            
            down_col1, down_col2 = st.columns(2)
            base_filename = uploaded_file.name.split('.')[0]
            
            with down_col1:
                csv_data = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Scarica in formato CSV",
                    data=csv_data,
                    file_name=f"{base_filename}.csv",
                    mime="text/csv",
                )
                
            with down_col2:
                try:
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        df.to_excel(writer, sheet_name='Dati_Attivita', index=False)
                    
                    st.download_button(
                        label="📊 Scarica in formato Excel",
                        data=buffer.getvalue(),
                        file_name=f"{base_filename}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except Exception as excel_err:
                    st.info(f"Esportazione Excel non disponibile temporaneamente ({excel_err})")
                    
            st.write(f"ℹ️ **Riepilogo colonne:** {len(df.columns)} elementi tracciati | **Righe totali:** {len(df)}")

    except Exception as e:
        st.error(f"❌ Si è verificato un errore durante l'elaborazione del file: {e}")
        with st.expander("🔍 Dettagli tecnici dell'errore (Debug)"):
            import traceback
            st.code(traceback.format_exc())
            
    finally:
        # Pulizia rigorosa del file temporaneo sul server
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except:
                pass
