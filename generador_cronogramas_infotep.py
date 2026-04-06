import streamlit as st
import pandas as pd
import json
import os
from io import BytesIO
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from fillpdf import fillpdfs

# --- CONFIGURACIÓN DE INGENIERÍA ---
# Esta es la dirección de tu carpeta "REPOSITORIO_INFOTEP_2026"
ID_CARPETA_DESTINO = "1X-dNqrDVubLCqZyLh2rzHWFhZb47R0-m" 
PLANTILLA = "PLANTILLA_FINAL.pdf"

st.set_page_config(page_title="Laboratorio PDF - Leonel Tavarez", layout="wide")

# --- FUNCIÓN DE CONEXIÓN SEGURA ---
def get_drive_service():
    try:
        # Extraemos la llave desde los Secrets de Streamlit
        creds_info = json.loads(st.secrets["google_creds"]["json_data"])
        if "private_key" in creds_info:
            creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
        
        creds = service_account.Credentials.from_service_account_info(
            creds_info, 
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        st.error(f"Error de autenticación con Google: {e}")
        return None

# --- FUNCIÓN DE SUBIDA (SIN CACHE) ---
def subir_a_drive(pdf_bytes, nombre_archivo):
    service = get_drive_service()
    if not service: return False
    
    metadata = {
        'name': nombre_archivo,
        'parents': [ID_CARPETA_DESTINO]
    }
    
    # Usamos BytesIO para que el archivo viaje por la memoria, no por el disco
    media = MediaIoBaseUpload(
        BytesIO(pdf_bytes), 
        mimetype='application/pdf', 
        resumable=True
    )
    
    try:
        service.files().create(
            body=metadata, 
            media_body=media, 
            supportsAllDrives=True
        ).execute()
        return True
    except Exception as e:
        st.error(f"Error al subir {nombre_archivo}: {e}")
        return False

# --- INTERFAZ DEL LABORATORIO ---
st.title("🧪 Laboratorio de Automatización PDF v2.0")
st.markdown("---")

# Carga de datos directamente de tu Google Sheets oficial
@st.cache_data(ttl=0)
def load_data():
    url = "https://docs.google.com/spreadsheets/d/1SiA8b7PAWOlTUfrHu_ew3Qt-D1JTVSZKQ8bUbSS4GQU/gviz/tq?tqx=out:csv"
    return pd.read_csv(url)

try:
    df = load_data()
    # Filtro de empresas único y ordenado
    empresa_sel = st.selectbox("Selecciona la Empresa para Procesar", sorted(df['EMPRESA'].unique()))
    
    if st.button("🚀 Generar y Enviar a Drive"):
        # Filtramos las acciones formativas de esa empresa
        acciones = df[df['EMPRESA'] == empresa_sel]['ACCION_FORMATIVA'].unique().tolist()
        
        if not acciones:
            st.warning("No se encontraron acciones formativas para esta empresa.")
        else:
            with st.status("Procesando cronogramas...", expanded=True) as status:
                # Lógica de bloques de 10 acciones por página
                for i in range(0, len(acciones), 10):
                    lote = acciones[i:i+10]
                    pagina = (i // 10) + 1
                    
                    # Preparamos el diccionario para fillpdf
                    datos_pdf = {'txt_empresa': empresa_sel, 'txt_regional': 'Cibao Norte'}
                    for idx, valor in enumerate(lote):
                        datos_pdf[f'accion_{idx+1}'] = valor
                    
                    # Nombre temporal y generación
                    temp_file = f"temp_p{pagina}.pdf"
                    fillpdfs.write_fillable_pdf(PLANTILLA, temp_file, datos_pdf)
                    
                    # Leemos y subimos
                    with open(temp_file, "rb") as f:
                        archivo_final = f"Cronograma_{empresa_sel}_P{pagina}.pdf"
                        if subir_a_drive(f.read(), archivo_final):
                            st.write(f"✅ Enviado con éxito: {archivo_final}")
                    
                    # Limpieza inmediata de archivos temporales
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                
                status.update(label="¡Misión cumplida!", state="complete")
            
            st.success(f"Todos los archivos de **{empresa_sel}** están ahora en tu Google Drive.")

except Exception as e:
    st.error(f"Ocurrió un error en la aplicación: {e}")