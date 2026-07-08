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

# BUG FIX #9: Supporta sia .fit che .zip
uploaded_file = st.file_uploader(
    "Trascina o seleziona un file .fit o .zip (da Garmin)",
    type=["fit", "zip", "FIT", "ZIP"],
    help="Supporta file .fit direttamente o .zip scaricato da Garmin Connect"
)

if uploaded_file is not None:
    st.info(f"📂 File caricato: **{uploaded_file.name}**")
    
    # BUG FIX #10: Estrai il .fit se il file è un .zip
    if uploaded_file.name.lower().endswith('.zip'):
        st.write("🔍 Rilevato file compresso .zip - Estrazione in corso...")
        
        import zipfile
        
        try:
            with tempfile.TemporaryDirectory() as extract_dir:
                # Estrai il zip
                with zipfile.ZipFile(io.BytesIO(uploaded_file.getvalue())) as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                # Trova il file .fit
                fit_files = []
                for root, dirs, files in os.walk(extract_dir):
                    for file in files:
                        if file.lower().endswith('.fit'):
                            fit_files.append(os.path.join(root, file))
                
                if not fit_files:
                    st.error("❌ Nessun file .fit trovato nello zip!")
                    st.info("Il file zip potrebbe avere una struttura diversa. Prova a estrarlo manualmente.")
                    st.stop()
                
                if len(fit_files) > 1:
                    st.warning(f"⚠️ Trovati {len(fit_files)} file .fit nello zip. Uso il primo...")
                
                fit_path = fit_files[0]
                st.success(f"✅ File estratto: {os.path.basename(fit_path)}")
                
                # Leggi il file estratto
                with open(fit_path, 'rb') as f:
                    fit_data = f.read()
                
                # Crea un file temporaneo dal contenuto
                with tempfile.NamedTemporaryFile(delete=False, suffix=".fit") as tmp:
                    tmp.write(fit_data)
                    tmp_path = tmp.name
        
        except zipfile.BadZipFile:
            st.error("❌ File zip corrotto. Prova a scaricarlo di nuovo da Garmin Connect.")
            st.stop()
        except Exception as e:
            st.error(f"❌ Errore estrazione: {e}")
            st.stop()
    
    elif uploaded_file.name.lower().endswith('.fit'):
        st.success(f"✅ File .fit riconosciuto")
        
        # BUG FIX #11: Crea file temporaneo dal contenuto
        with tempfile.NamedTemporaryFile(delete=False, suffix=".fit") as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name
    
    else:
        st.error("❌ Formato non supportato. Usa .fit o .zip")
        st.stop()
    
    # BUG FIX #12: Verifica che il file sia valido
    file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
    
    if file_size_mb > 50:
        st.error(f"❌ File troppo grande ({file_size_mb:.1f} MB). Massimo 50 MB.")
        st.stop()
    
    st.info(f"📊 Analisi in corso... ({file_size_mb:.1f} MB)")
    
    # ... resto del codice rimane uguale da qui in poi
        
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
