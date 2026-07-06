import streamlit as st
import pandas as pd
from fitparse import FitFile
import tempfile
import os
import io
from datetime import datetime

st.set_page_config(page_title="FIT to CSV Converter", layout="wide")
st.title("🚴‍♂️ Convertitore FIT ➡️ CSV (Avanzato)")
st.write("Estrai TUTTI i dati da file .fit con opzioni avanzate")

# Sidebar per configurazione
st.sidebar.header("⚙️ Opzioni Avanzate")
extract_mode = st.sidebar.radio(
    "Cosa estrarre?",
    ["Solo Records (Dati continui)", "Tutti i messaggi FIT", "Records + Statistiche"]
)

# Widget per caricare il file
uploaded_file = st.file_uploader("Scegli un file .fit", type="fit")

if uploaded_file is not None:
    st.info("📊 Analisi del file in corso...")
    
    # Salvataggio temporaneo
    with tempfile.NamedTemporaryFile(delete=False, suffix=".fit") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name
    
    try:
        fitfile = FitFile(tmp_path)
        
        # === MODALITÀ 1: SOLO RECORDS ===
        if extract_mode == "Solo Records (Dati continui)":
            records = []
            for record in fitfile.get_messages('record'):
                record_data = {}
                for data in record:
                    value = data.value
                    if isinstance(value, (list, tuple)):
                        value = str(value)
                    record_data[data.name] = value
                records.append(record_data)
            
            if records:
                df = pd.DataFrame(records)
                
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                
                st.success(f"✅ File elaborato! {len(df)} record trovati")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Record estratti", len(df))
                with col2:
                    if 'timestamp' in df.columns:
                        duration = (df['timestamp'].max() - df['timestamp'].min())
                        st.metric("Durata", str(duration).split('.')[0])
                
                st.write("### 📋 Anteprima dati:")
                st.dataframe(df.head(10), use_container_width=True)
                
                st.write("### 📊 Statistiche campi numerici:")
                numeric_cols = df.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0:
                    stats_df = df[numeric_cols].describe()
                    st.dataframe(stats_df, use_container_width=True)
            else:
                st.warning("⚠️ Nessun record continuo trovato in questo file")
                df = pd.DataFrame()
        
        # === MODALITÀ 2: TUTTI I MESSAGGI ===
        elif extract_mode == "Tutti i messaggi FIT":
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
            
            st.success(f"✅ File elaborato! Trovati {len(all_messages)} tipi di messaggi")
            
            st.write("### 📝 Tipi di messaggi trovati:")
            for msg_type, messages in all_messages.items():
                st.write(f"**{msg_type}**: {len(messages)} record")
            
            selected_msg = st.selectbox(
                "Seleziona il tipo di messaggio da esportare",
                list(all_messages.keys())
            )
            
            df = pd.DataFrame(all_messages[selected_msg])
            
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            
            st.write(f"### 📋 Dati ({selected_msg}):")
            st.dataframe(df.head(10), use_container_width=True)
        
        # === MODALITÀ 3: RECORDS + STATISTICHE ===
        else:
            records = []
            
            for record in fitfile.get_messages('record'):
                record_data = {}
                for data in record:
                    value = data.value
                    if isinstance(value, (list, tuple)):
                        value = str(value)
                    record_data[data.name] = value
                records.append(record_data)
            
            if records:
                df = pd.DataFrame(records)
                
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                
                st.success(f"✅ File elaborato! {len(df)} record trovati")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Record", len(df))
                with col2:
                    if 'timestamp' in df.columns:
                        duration = (df['timestamp'].max() - df['timestamp'].min())
                        st.metric("Durata", str(duration).split('.')[0])
                with col3:
                    if 'distance' in df.columns:
                        dist = df['distance'].max() / 1000
                        st.metric("Distanza", f"{dist:.2f} km")
                with col4:
                    if 'heart_rate' in df.columns:
                        avg_hr = df['heart_rate'].mean()
                        st.metric("FC Media", f"{avg_hr:.0f} bpm")
                
                st.write("### 📋 Dati completi:")
                st.dataframe(df, use_container_width=True)
            else:
                st.warning("⚠️ Nessun record trovato")
                df = pd.DataFrame()
        
        # === DOWNLOAD ===
        if not df.empty:
            st.divider()
            st.write("### 💾 Scarica i dati:")
            
            col1, col2 = st.columns(2)
            
            with col1:
                csv_data = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Scarica CSV",
                    data=csv_data,
                    file_name=f"{uploaded_file.name.split('.')[0]}.csv",
                    mime="text/csv",
                )
            
            with col2:
                try:
                    # Ottimizzazione: Creazione Excel in memoria (senza salvare su disco)
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        df.to_excel(writer, sheet_name='Data', index=False)
                    
                    st.download_button(
                        label="📊 Scarica Excel",
                        data=buffer.getvalue(),
                        file_name=f"{uploaded_file.name.split('.')[0]}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except Exception as e:
                    st.info(f"(Excel non disponibile: {e})")
            
            st.write("### ℹ️ Info file:")
            info_col1, info_col2 = st.columns(2)
            with info_col1:
                st.write(f"**Campi estratti**: {len(df.columns)}")
                st.write(f"**Righe**: {len(df)}")
            with info_col2:
                st.write(f"**Colonne**: {', '.join(df.columns[:5])}...")
    
    except Exception as e:
        st.error(f"❌ Errore durante la lettura del file: {e}")
        st.info("Verifica che sia un file .fit valido.")
        import traceback
        st.write("Debug info:")
        st.code(traceback.format_exc())
    
    finally:
        # Pulizia dell'unico file temporaneo reale
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
