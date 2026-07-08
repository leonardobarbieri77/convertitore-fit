import streamlit as st
import pandas as pd
from fitparse import FitFile
import tempfile
import os
import io
from datetime import datetime
import sys

st.set_page_config(page_title="FIT Converter", layout="wide", initial_sidebar_state="expanded")
st.title("🚴‍♂️ FIT ➡️ CSV (Mobile Friendly)")
st.write("Estrai dati da file .fit - Funziona su desktop e mobile (Pixel, iOS)")

# ═══════════════════════════════════════════════════════════════
# CONFIGURAZIONE
# ═══════════════════════════════════════════════════════════════
st.sidebar.header("⚙️ Opzioni")
extract_mode = st.sidebar.radio(
    "Modalità estrazione:",
    ["Records (Dati continui)", "Tutti i messaggi", "Records + Statistiche"],
    help="Scegli cosa estrarre dal file FIT"
)

# BUG FIX #1: Aggiungi informazioni su compatibilità
is_mobile = "Android" in st.session_state.get("user_agent", "") or "iPhone" in st.session_state.get("user_agent", "")
if is_mobile:
    st.sidebar.info("📱 Modalità Mobile attiva - Ottimizzato per Pixel/iPhone")

# ═══════════════════════════════════════════════════════════════
# CARICAMENTO FILE
# ═══════════════════════════════════════════════════════════════
st.write("### 📥 Carica un file .fit")

# BUG FIX #13: File browser integrato
if 'current_path' not in st.session_state:
    # Inizializza con Downloads
    if os.name == 'nt':  # Windows
        st.session_state.current_path = os.path.expanduser("~/Downloads")
    else:  # Linux/Mac/Android
        st.session_state.current_path = os.path.expanduser("~/Downloads")
        # Se Downloads non esiste, usa home
        if not os.path.exists(st.session_state.current_path):
            st.session_state.current_path = os.path.expanduser("~")

uploaded_file = None
fit_data = None

# Mostra il percorso corrente
st.write(f"📂 **Percorso**: `{st.session_state.current_path}`")

# Bottone per tornare alla home
col1, col2 = st.columns([1, 1])
with col1:
    if st.button("🏠 Home"):
        st.session_state.current_path = os.path.expanduser("~")
        st.rerun()

with col2:
    if st.button("📥 Downloads"):
        st.session_state.current_path = os.path.expanduser("~/Downloads")
        st.rerun()

try:
    # Elenca file e cartelle
    items = os.listdir(st.session_state.current_path)
    folders = [item for item in items if os.path.isdir(os.path.join(st.session_state.current_path, item))]
    files = [item for item in items if os.path.isfile(os.path.join(st.session_state.current_path, item))]
    
    # Ordina
    folders.sort()
    files.sort()
    
    # Mostra cartelle
    if folders:
        st.write("**📁 Cartelle:**")
        cols = st.columns(3)
        for idx, folder in enumerate(folders):
            with cols[idx % 3]:
                if st.button(f"📂 {folder}", key=f"folder_{folder}"):
                    st.session_state.current_path = os.path.join(st.session_state.current_path, folder)
                    st.rerun()
    
    # Filtra file .fit e .zip
    fit_files = [f for f in files if f.lower().endswith(('.fit', '.zip'))]
    other_files = [f for f in files if not f.lower().endswith(('.fit', '.zip'))]
    
    # Mostra file .fit e .zip evidenziati
    if fit_files:
        st.write("**✅ File .fit/.zip (Pronti):**")
        for file in fit_files:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"🎯 {file}")
            with col2:
                if st.button("📥 Carica", key=f"load_{file}"):
                    file_path = os.path.join(st.session_state.current_path, file)
                    with open(file_path, 'rb') as f:
                        fit_data = f.read()
                    st.session_state.selected_file = file
                    st.success(f"✅ File caricato: {file}")
                    st.rerun()
    
    # Mostra altri file (grigi)
    if other_files:
        with st.expander(f"📄 Vedi altri file ({len(other_files)})"):
            for file in other_files[:20]:  # Mostra max 20
                st.write(f"  └─ {file}")
    
    # Bottone per salire di livello
    if st.session_state.current_path != os.path.expanduser("~"):
        if st.button("⬆️ Torna indietro"):
            st.session_state.current_path = os.path.dirname(st.session_state.current_path)
            st.rerun()

except PermissionError:
    st.error(f"❌ Permesso negato: {st.session_state.current_path}")
except Exception as e:
    st.error(f"❌ Errore nella navigazione: {e}")

# Se file è stato caricato
if fit_data is not None:
        
        # Leggi il file FIT
        try:
            fitfile = FitFile(tmp_path)
        except Exception as e:
            st.error(f"❌ File .fit non valido: {e}")
            st.info("Verifica che sia un file Garmin/Apple Watch autentico")
            st.stop()
        
        # === MODALITÀ 1: SOLO RECORDS ===
        if extract_mode == "Records (Dati continui)":
            records = []
            
            try:
                for record in fitfile.get_messages('record'):
                    record_data = {}
                    for data in record:
                        try:
                            value = data.value
                            # Gestisci liste e valori speciali
                            if isinstance(value, (list, tuple)):
                                value = str(value)
                            elif value is None:
                                value = ""
                            record_data[data.name] = value
                        except:
                            pass
                    records.append(record_data)
            except Exception as e:
                st.error(f"Errore lettura records: {e}")
                st.stop()
            
            if records:
                df = pd.DataFrame(records)
                
                # BUG FIX #6: Converti timestamp in modo sicuro
                if 'timestamp' in df.columns:
                    try:
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                    except:
                        pass
                
                st.success(f"✅ {len(df)} record estratti")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Record", len(df))
                with col2:
                    if 'timestamp' in df.columns:
                        try:
                            duration = df['timestamp'].max() - df['timestamp'].min()
                            st.metric("Durata", str(duration).split('.')[0])
                        except:
                            st.metric("Durata", "N/A")
                
                st.write("### 📋 Anteprima:")
                st.dataframe(df.head(10), use_container_width=True)
                
                # Statistiche
                numeric_cols = df.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0:
                    st.write("### 📊 Statistiche:")
                    st.dataframe(df[numeric_cols].describe(), use_container_width=True)
            else:
                st.warning("⚠️ Nessun record trovato in questo file")
        
        # === MODALITÀ 2: TUTTI I MESSAGGI ===
        elif extract_mode == "Tutti i messaggi":
            all_messages = {}
            
            try:
                for message in fitfile.get_messages():
                    msg_type = message.name
                    if msg_type not in all_messages:
                        all_messages[msg_type] = []
                    
                    msg_data = {}
                    for data in message:
                        try:
                            value = data.value
                            if isinstance(value, (list, tuple)):
                                value = str(value)
                            elif value is None:
                                value = ""
                            msg_data[data.name] = value
                        except:
                            pass
                    
                    all_messages[msg_type].append(msg_data)
            except Exception as e:
                st.error(f"Errore lettura messaggi: {e}")
                st.stop()
            
            st.success(f"✅ {len(all_messages)} tipi di messaggi trovati")
            
            st.write("### 📝 Tipi di messaggi:")
            msg_summary = {msg: len(msgs) for msg, msgs in all_messages.items()}
            st.write(msg_summary)
            
            selected_msg = st.selectbox("Seleziona messaggio da esportare", list(all_messages.keys()))
            df = pd.DataFrame(all_messages[selected_msg])
            
            if 'timestamp' in df.columns:
                try:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                except:
                    pass
            
            st.dataframe(df.head(10), use_container_width=True)
        
        # === MODALITÀ 3: RECORDS + STATISTICHE ===
        else:
            records = []
            
            try:
                for record in fitfile.get_messages('record'):
                    record_data = {}
                    for data in record:
                        try:
                            value = data.value
                            if isinstance(value, (list, tuple)):
                                value = str(value)
                            elif value is None:
                                value = ""
                            record_data[data.name] = value
                        except:
                            pass
                    records.append(record_data)
            except Exception as e:
                st.error(f"Errore lettura records: {e}")
                st.stop()
            
            if records:
                df = pd.DataFrame(records)
                
                if 'timestamp' in df.columns:
                    try:
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                    except:
                        pass
                
                st.success(f"✅ {len(df)} record elaborati")
                
                # Metriche
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Record", len(df))
                with col2:
                    if 'timestamp' in df.columns:
                        try:
                            duration = df['timestamp'].max() - df['timestamp'].min()
                            st.metric("Durata", str(duration).split('.')[0])
                        except:
                            st.metric("Durata", "N/A")
                with col3:
                    if 'distance' in df.columns:
                        try:
                            dist = df['distance'].max() / 1000
                            st.metric("Km", f"{dist:.2f}")
                        except:
                            st.metric("Km", "N/A")
                with col4:
                    if 'heart_rate' in df.columns:
                        try:
                            avg_hr = df['heart_rate'].mean()
                            st.metric("FC Media", f"{avg_hr:.0f} bpm")
                        except:
                            st.metric("FC Media", "N/A")
                
                st.write("### 📋 Dati completi:")
                st.dataframe(df, use_container_width=True)
        
        # === DOWNLOAD ===
        if not df.empty:
            st.divider()
            st.write("### 💾 Scarica dati:")
            
            col1, col2 = st.columns(2)
            
            with col1:
                csv_data = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 CSV",
                    data=csv_data,
                    file_name=f"{uploaded_file.name.split('.')[0]}.csv",
                    mime="text/csv",
                )
            
            with col2:
                try:
                    # BUG FIX #7: Crea Excel in memoria (no file su disco)
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        df.to_excel(writer, sheet_name='Data', index=False)
                    
                    buffer.seek(0)
                    
                    st.download_button(
                        label="📊 Excel",
                        data=buffer.getvalue(),
                        file_name=f"{uploaded_file.name.split('.')[0]}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except Exception as e:
                    st.info(f"❌ Excel: {str(e)[:50]}")
            
            st.write(f"**Campi**: {len(df.columns)} | **Righe**: {len(df)}")
    
    except Exception as e:
        st.error(f"❌ Errore: {e}")
        import traceback
        with st.expander("🔍 Debug"):
            st.code(traceback.format_exc())
    
    finally:
        # BUG FIX #8: Pulizia aggressiva
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except:
                pass
        
        # Rilascia memoria
        del fitfile if 'fitfile' in locals() else None
        import gc
        gc.collect()
