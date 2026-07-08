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

# ═══════════════════════════════════════════════════════════════
# FILE BROWSER
# ═══════════════════════════════════════════════════════════════
st.write("### 📥 Carica un file .fit")

if 'current_path' not in st.session_state:
    st.session_state.current_path = os.path.expanduser("~/Downloads")
    if not os.path.exists(st.session_state.current_path):
        st.session_state.current_path = os.path.expanduser("~")

fit_data = None
tmp_path = None
df = pd.DataFrame()

st.write(f"📂 **Percorso**: `{st.session_state.current_path}`")

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
    items = os.listdir(st.session_state.current_path)
    folders = [item for item in items if os.path.isdir(os.path.join(st.session_state.current_path, item))]
    files = [item for item in items if os.path.isfile(os.path.join(st.session_state.current_path, item))]
    
    folders.sort()
    files.sort()
    
    if folders:
        st.write("**📁 Cartelle:**")
        cols = st.columns(3)
        for idx, folder in enumerate(folders):
            with cols[idx % 3]:
                if st.button(f"📂 {folder}", key=f"folder_{folder}"):
                    st.session_state.current_path = os.path.join(st.session_state.current_path, folder)
                    st.rerun()
    
    fit_files = [f for f in files if f.lower().endswith(('.fit', '.zip'))]
    other_files = [f for f in files if not f.lower().endswith(('.fit', '.zip'))]
    
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
    
    if other_files:
        with st.expander(f"📄 Vedi altri file ({len(other_files)})"):
            for file in other_files[:20]:
                st.write(f"  └─ {file}")
    
    if st.session_state.current_path != os.path.expanduser("~"):
        if st.button("⬆️ Torna indietro"):
            st.session_state.current_path = os.path.dirname(st.session_state.current_path)
            st.rerun()

except PermissionError:
    st.error(f"❌ Permesso negato: {st.session_state.current_path}")
except Exception as e:
    st.error(f"❌ Errore: {e}")

# ═══════════════════════════════════════════════════════════════
# PROCESSAMENTO FILE
# ═══════════════════════════════════════════════════════════════
if 'selected_file' in st.session_state and fit_data is None:
    selected_file = st.session_state.selected_file
    file_path = os.path.join(st.session_state.current_path, selected_file)
    if os.path.exists(file_path):
        with open(file_path, 'rb') as f:
            fit_data = f.read()

if fit_data is not None:
    file_size_mb = len(fit_data) / (1024 * 1024)
    
    if file_size_mb > 50:
        st.error(f"❌ File troppo grande ({file_size_mb:.1f} MB)")
        st.stop()
    
    st.info(f"📊 Analisi in corso... ({file_size_mb:.1f} MB)")
    
    try:
        if 'selected_file' in st.session_state and st.session_state.selected_file.lower().endswith('.zip'):
            import zipfile
            st.write("🔍 Estrazione zip...")
            
            with tempfile.TemporaryDirectory() as extract_dir:
                with zipfile.ZipFile(io.BytesIO(fit_data)) as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                fit_files = []
                for root, dirs, files_list in os.walk(extract_dir):
                    for file in files_list:
                        if file.lower().endswith('.fit'):
                            fit_files.append(os.path.join(root, file))
                
                if not fit_files:
                    st.error("❌ Nessun .fit nello zip!")
                    st.stop()
                
                with open(fit_files[0], 'rb') as f:
                    fit_data = f.read()
                
                st.success(f"✅ Estratto: {os.path.basename(fit_files[0])}")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".fit") as tmp:
            tmp.write(fit_data)
            tmp_path = tmp.name
        
        if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
            st.error("❌ Errore file temporaneo")
            st.stop()
        
        fitfile = FitFile(tmp_path)
        
        # ═══════════════════════════════════════════════════════════════
        # MODALITÀ 1: RECORDS
        # ═══════════════════════════════════════════════════════════════
        if extract_mode == "Records (Dati continui)":
            records = []
            
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
            
            if records:
                df = pd.DataFrame(records)
                
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
                
                numeric_cols = df.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0:
                    st.write("### 📊 Statistiche:")
                    st.dataframe(df[numeric_cols].describe(), use_container_width=True)
            else:
                st.warning("⚠️ Nessun record trovato")
        
        # ═══════════════════════════════════════════════════════════════
        # MODALITÀ 2: TUTTI I MESSAGGI
        # ═══════════════════════════════════════════════════════════════
        elif extract_mode == "Tutti i messaggi":
            all_messages = {}
            
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
            
            st.success(f"✅ {len(all_messages)} tipi di messaggi")
            
            st.write("### 📝 Tipi:")
            for msg, msgs in all_messages.items():
                st.write(f"  • {msg}: {len(msgs)}")
            
            selected_msg = st.selectbox("Seleziona messaggio", list(all_messages.keys()))
            df = pd.DataFrame(all_messages[selected_msg])
            
            if 'timestamp' in df.columns:
                try:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                except:
                    pass
            
            st.dataframe(df.head(10), use_container_width=True)
        
        # ═══════════════════════════════════════════════════════════════
        # MODALITÀ 3: RECORDS + STATISTICHE
        # ═══════════════════════════════════════════════════════════════
        else:
            records = []
            
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
            
            if records:
                df = pd.DataFrame(records)
                
                if 'timestamp' in df.columns:
                    try:
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                    except:
                        pass
                
                st.success(f"✅ {len(df)} record")
                
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
                
                st.write("### 📋 Dati:")
                st.dataframe(df, use_container_width=True)
        
        # ═══════════════════════════════════════════════════════════════
        # DOWNLOAD
        # ═══════════════════════════════════════════════════════════════
        if not df.empty:
            st.divider()
            st.write("### 💾 Scarica:")
            
            col1, col2 = st.columns(2)
            
            with col1:
                csv_data = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 CSV",
                    data=csv_data,
                    file_name=f"{st.session_state.get('selected_file', 'data')}.csv",
                    mime="text/csv",
                )
            
            with col2:
                try:
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        df.to_excel(writer, sheet_name='Data', index=False)
                    buffer.seek(0)
                    
                    st.download_button(
                        label="📊 Excel",
                        data=buffer.getvalue(),
                        file_name=f"{st.session_state.get('selected_file', 'data')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except:
                    st.info("❌ Excel non disponibile")
    
    except Exception as e:
        st.error(f"❌ Errore: {e}")
        with st.expander("🔍 Debug"):
            import traceback
            st.code(traceback.format_exc())
    
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except:
                pass
        import gc
        gc.collect()
