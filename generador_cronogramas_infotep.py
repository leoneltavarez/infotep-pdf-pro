import streamlit as st
import pandas as pd
import fillpdf
from fillpdf import fillpdfs
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- 1. CONFIGURACIÓN DE LA APP ---
st.set_page_config(page_title="Generador INFOTEP", layout="wide")
st.title("🚀 Sistema de Automatización - INFOTEP 2026")

# --- 2. CONEXIÓN CON GOOGLE DRIVE ---
try:
    creds_info = json.loads(st.secrets["google_creds"]["json_data"])
    creds = service_account.Credentials.from_service_account_info(creds_info)
    drive_service = build('drive', 'v3', credentials=creds)
except Exception as e:
    st.error(f"❌ Error en Secrets (JSON): {e}")

# IDs fijos de tu configuración
PARENT_FOLDER_ID = "1X-dNqrDVubLCqZyLh2rzHWFhZb47R0-m"
PLANTILLA = "PLANTILLA_FINAL.pdf"

# --- 3. MOTOR DE LECTURA DE EXCEL (GOOGLE SHEETS) ---
@st.cache_data
def cargar_datos():
    sheet_id = "1SiA8b7PAWOlTUfrHu_ew3Qt-D1JTVSZKQ8bUbSS4GQU"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    data = pd.read_csv(url)
    # Limpiamos nombres de columnas (Mayúsculas y sin espacios)
    data.columns = [str(c).strip().upper() for c in data.columns]
    return data

try:
    df = cargar_datos()
    # Buscador inteligente de la columna 'EMPRESA'
    col_empresa = [c for c in df.columns if 'EMPRESA' in c][0]
    lista_empresas = sorted(df[col_empresa].dropna().unique())
    empresa_sel = st.selectbox("🎯 Seleccione la Empresa:", lista_empresas)
except Exception as e:
    st.error(f"❌ No se pudo cargar el Excel: {e}")
    df = None

# --- 4. FUNCIONES DE DRIVE (CORRECCIÓN DE CUOTA) ---
def obtener_o_crear_carpeta(nombre_carpeta):
    query = f"name = '{nombre_carpeta}' and '{PARENT_FOLDER_ID}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    # El parámetro supportsAllDrives permite que el robot trabaje en tu carpeta compartida
    respuesta = drive_service.files().list(q=query, supportsAllDrives=True, includeItemsFromAllDrives=True).execute().get('files', [])
    
    if respuesta:
        return respuesta[0]['id']
    
    meta = {
        'name': nombre_carpeta, 
        'mimeType': 'application/vnd.google-apps.folder', 
        'parents': [PARENT_FOLDER_ID]
    }
    return drive_service.files().create(body=meta, fields='id', supportsAllDrives=True).execute().get('id')

# --- 5. BOTÓN DE GENERACIÓN ---
if st.button("🛠️ Generar Cronograma y Subir a Drive"):
    if df is not None:
        if not os.path.exists(PLANTILLA):
            st.error(f"❌ Error: El archivo {PLANTILLA} no está en tu repositorio de GitHub.")
        else:
            try:
                with st.spinner(f"Generando PDF para {empresa_sel}..."):
                    # Buscador inteligente de columna de acciones
                    col_accion = [c for c in df.columns if 'ACCION' in c or 'FORMATIVA' in c][0]
                    datos_empresa = df[df[col_empresa] == empresa_sel]
                    
                    # Consolidar acciones formativas en un solo bloque de texto
                    texto_acciones = "\n".join(datos_empresa[col_accion].astype(str).tolist())
                    
                    # Ruta temporal en la nube (Streamlit requiere /tmp/)
                    nombre_archivo = f"Cronograma_{empresa_sel.replace(' ', '_')}.pdf"
                    ruta_tmp = os.path.join("/tmp", nombre_archivo)
                    
                    # Mapeo de campos para tu PDF
                    campos = {
                        'Empresa': empresa_sel,
                        'Dirección Regional': 'Cibao Norte',
                        'Acciones de Capacitación': texto_acciones
                    }
                    
                    # 1. Ejecutar el llenado del PDF
                    fillpdfs.write_fillable_pdf(PLANTILLA, ruta_tmp, campos)
                    
                    # 2. Asegurar que existe la carpeta de la empresa
                    id_subcarpeta = obtener_o_crear_carpeta(empresa_sel)
                    
                    # 3. Subir el archivo final (supportsAllDrives usa TU espacio de Drive)
                    meta_file = {'name': nombre_archivo, 'parents': [id_subcarpeta]}
                    media = MediaFileUpload(ruta_tmp, mimetype='application/pdf')
                    
                    drive_service.files().create(
                        body=meta_file, 
                        media_body=media, 
                        supportsAllDrives=True 
                    ).execute()
                    
                    st.success(f"✅ ¡Éxito! El cronograma de {empresa_sel} con {len(datos_empresa)} acciones se guardó en Drive.")
            except Exception as e:
                st.error(f"❌ Error en el motor: {e}")
