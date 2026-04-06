import streamlit as st
import pandas as pd
import fillpdf
from fillpdf import fillpdfs
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- 1. CONFIGURACIÓN DE INTERFAZ ---
st.set_page_config(page_title="Generador INFOTEP", layout="wide")
st.title("🚀 Sistema de Automatización - INFOTEP 2026")

# --- 2. CONEXIÓN CON GOOGLE DRIVE ---
try:
    creds_info = json.loads(st.secrets["google_creds"]["json_data"])
    creds = service_account.Credentials.from_service_account_info(creds_info)
    drive_service = build('drive', 'v3', credentials=creds)
except Exception as e:
    st.error(f"❌ Error en Secrets (JSON): {e}")

# IDs fijos
PARENT_FOLDER_ID = "1X-dNqrDVubLCqZyLh2rzHWFhZb47R0-m"
PLANTILLA = "PLANTILLA_FINAL.pdf"

# --- 3. MOTOR DE DATOS (LECTURA DEL EXCEL) ---
@st.cache_data
def cargar_datos():
    # Tu ID de hoja de Google Sheets
    sheet_id = "1SiA8b7PAWOlTUfrHu_ew3Qt-D1JTVSZKQ8bUbSS4GQU"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    data = pd.read_csv(url)
    data.columns = data.columns.str.strip() # Limpia espacios en nombres de columnas
    return data

try:
    df = cargar_datos()
    lista_empresas = sorted(df['EMPRESA'].dropna().unique())
    empresa_sel = st.selectbox("🎯 Seleccione la Empresa:", lista_empresas)
except Exception as e:
    st.error(f"❌ Error al cargar empresas: {e}")
    df = None

# --- 4. FUNCIONES DE CARPETAS ---
def obtener_o_crear_carpeta(nombre_carpeta):
    query = f"name = '{nombre_carpeta}' and '{PARENT_FOLDER_ID}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    respuesta = drive_service.files().list(q=query).execute().get('files', [])
    if respuesta:
        return respuesta[0]['id']
    meta = {'name': nombre_carpeta, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [PARENT_FOLDER_ID]}
    return drive_service.files().create(body=meta, fields='id').execute().get('id')

# --- 5. EJECUCIÓN ---
if st.button("🛠️ Generar y Subir a Drive"):
    if df is not None:
        if not os.path.exists(PLANTILLA):
            st.error(f"❌ No se encuentra el archivo {PLANTILLA} en el repositorio.")
        else:
            try:
                with st.spinner(f"Generando cronograma para {empresa_sel}..."):
                    # Filtro de datos
                    datos_filtro = df[df['EMPRESA'] == empresa_sel]
                    
                    # Preparar archivo temporal (INDISPENSABLE EN LA NUBE)
                    nombre_pdf = f"Cronograma_{empresa_sel.replace(' ', '_')}.pdf"
                    ruta_temp = os.path.join("/tmp", nombre_pdf)
                    
                    # Mapeo de campos (Asegúrate que coincidan con tu PDF)
                    campos_pdf = {
                        'Empresa': empresa_sel,
                        'Dirección Regional': 'Cibao Norte',
                        'Acciones de Capacitación': "\n".join(datos_filtro['ACCION FORMATIVA'].astype(str).tolist())
                    }
                    
                    # Llenado físico del PDF
                    fillpdfs.write_fillable_pdf(PLANTILLA, ruta_temp, campos_pdf)
                    
                    # Gestión en Google Drive
                    id_subcarpeta = obtener_o_crear_carpeta(empresa_sel)
                    meta_drive = {'name': nombre_pdf, 'parents': [id_subcarpeta]}
                    media = MediaFileUpload(ruta_temp, mimetype='application/pdf')
                    drive_service.files().create(body=meta_drive, media_body=media).execute()
                    
                    st.success(f"✅ ¡Proceso completado! Revisa la carpeta '{empresa_sel}' en tu Drive.")
            except Exception as e:
                st.error(f"❌ Error en el proceso: {e}")
