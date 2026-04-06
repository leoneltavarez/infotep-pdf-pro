import streamlit as st
import pandas as pd
import fillpdf
from fillpdf import fillpdfs
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Generador INFOTEP", layout="wide")
st.title("🚀 Sistema de Automatización - INFOTEP 2026")

# --- 2. CREDENCIALES ---
try:
    creds_info = json.loads(st.secrets["google_creds"]["json_data"])
    creds = service_account.Credentials.from_service_account_info(creds_info)
    drive_service = build('drive', 'v3', credentials=creds)
except Exception as e:
    st.error(f"❌ Error en Secrets de Streamlit: {e}")

# IDs de Referencia
PARENT_FOLDER_ID = "1X-dNqrDVubLCqZyLh2rzHWFhZb47R0-m" # Tu Repositorio 2026
PLANTILLA = "PLANTILLA_FINAL.pdf"

# --- 3. CARGA DE DATOS ---
@st.cache_data
def cargar_datos():
    sheet_id = "1SiA8b7PAWOlTUfrHu_ew3Qt-D1JTVSZKQ8bUbSS4GQU"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    data = pd.read_csv(url)
    # Limpiar nombres de columnas: quitar espacios y pasar a mayúsculas
    data.columns = [str(c).strip().upper() for c in data.columns]
    return data

try:
    df = cargar_datos()
    # Buscar columna de empresa que contenga la palabra 'EMPRESA'
    col_empresa = [c for c in df.columns if 'EMPRESA' in c][0]
    lista_empresas = sorted(df[col_empresa].dropna().unique())
    empresa_sel = st.selectbox("🎯 Seleccione la Empresa:", lista_empresas)
except Exception as e:
    st.error(f"❌ Error al leer el Excel: {e}")
    df = None

# --- 4. FUNCIONES DRIVE ---
def obtener_o_crear_carpeta(nombre_carpeta):
    query = f"name = '{nombre_carpeta}' and '{PARENT_FOLDER_ID}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    respuesta = drive_service.files().list(q=query).execute().get('files', [])
    if respuesta:
        return respuesta[0]['id']
    
    meta = {
        'name': nombre_carpeta,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [PARENT_FOLDER_ID]
    }
    return drive_service.files().create(body=meta, fields='id').execute().get('id')

# --- 5. BOTÓN DE ACCIÓN ---
if st.button("🛠️ Generar Cronograma y Subir"):
    if df is not None:
        if not os.path.exists(PLANTILLA):
            st.error(f"❌ No veo el archivo {PLANTILLA} en tu GitHub.")
        else:
            try:
                with st.spinner(f"Procesando {empresa_sel}..."):
                    # Detectar columna de acciones formativas
                    col_accion = [c for c in df.columns if 'ACCION' in c or 'FORMATIVA' in c][0]
                    
                    # Filtrar datos
                    datos_empresa = df[df[col_empresa] == empresa_sel]
                    
                    # Nombre y ruta temporal
                    nombre_archivo = f"Cronograma_{empresa_sel.replace(' ', '_')}.pdf"
                    ruta_tmp = os.path.join("/tmp", nombre_archivo)
                    
                    # Preparar campos para el PDF (Asegúrate que coincidan con tu plantilla)
                    campos = {
                        'Empresa': empresa_sel,
                        'Dirección Regional': 'Cibao Norte',
                        'Acciones de Capacitación': "\n".join(datos_empresa[col_accion].astype(str).tolist())
                    }
                    
                    # 1. Generar PDF en /tmp
                    fillpdfs.write_fillable_pdf(PLANTILLA, ruta_tmp, campos)
                    
                    # 2. Crear carpeta en Drive
                    id_subcarpeta = obtener_o_crear_carpeta(empresa_sel)
                    
                    # 3. Subir a Drive
                    meta_file = {'name': nombre_archivo, 'parents': [id_subcarpeta]}
                    media = MediaFileUpload(ruta_tmp, mimetype='application/pdf')
                    drive_service.files().create(body=meta_file, media_body=media).execute()
                    
                    st.success(f"✅ ¡Éxito! Archivo guardado en la carpeta '{empresa_sel}' de tu Drive.")
            except Exception as e:
                st.error(f"❌ Fallo en el motor: {e}")
