import streamlit as st
import pandas as pd
import fillpdf
from fillpdf import fillpdfs
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Generador INFOTEP 2026", layout="wide")
st.title("🚀 Sistema de Automatización - INFOTEP 2026")

try:
    creds_info = json.loads(st.secrets["google_creds"]["json_data"])
    creds = service_account.Credentials.from_service_account_info(creds_info)
    drive_service = build('drive', 'v3', credentials=creds)
except Exception as e:
    st.error(f"❌ Error en Secrets: {e}")

# ID de tu carpeta principal en Drive
PARENT_FOLDER_ID = "1X-dNqrDVubLCqZyLh2rzHWFhZb47R0-m"
PLANTILLA = "PLANTILLA_FINAL.pdf"

# --- 2. MOTOR DE DATOS ---
@st.cache_data
def cargar_datos():
    sheet_id = "1SiA8b7PAWOlTUfrHu_ew3Qt-D1JTVSZKQ8bUbSS4GQU"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    data = pd.read_csv(url)
    data.columns = [str(c).strip().upper() for c in data.columns]
    return data

try:
    df = cargar_datos()
    col_empresa = [c for c in df.columns if 'EMPRESA' in c][0]
    lista_empresas = sorted(df[col_empresa].dropna().unique())
    empresa_sel = st.selectbox("🎯 Seleccione la Empresa:", lista_empresas)
except Exception as e:
    st.error(f"❌ Error en base de datos: {e}")
    df = None

# --- 3. FUNCIÓN DE DRIVE ---
def obtener_o_crear_carpeta(nombre_carpeta):
    query = f"name = '{nombre_carpeta}' and '{PARENT_FOLDER_ID}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    respuesta = drive_service.files().list(q=query, supportsAllDrives=True, includeItemsFromAllDrives=True).execute().get('files', [])
    if respuesta: return respuesta[0]['id']
    
    meta = {'name': nombre_carpeta, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [PARENT_FOLDER_ID]}
    return drive_service.files().create(body=meta, fields='id', supportsAllDrives=True).execute().get('id')

# --- 4. EJECUCIÓN ---
if st.button("🛠️ Generar y Subir"):
    if df is not None:
        if not os.path.exists(PLANTILLA):
            st.error(f"❌ No se encuentra el archivo {PLANTILLA} en GitHub.")
        else:
            try:
                with st.spinner("Procesando..."):
                    col_accion = [c for c in df.columns if 'ACCION' in c or 'FORMATIVA' in c][0]
                    datos_empresa = df[df[col_empresa] == empresa_sel]
                    
                    nombre_archivo = f"Cronograma_{empresa_sel.replace(' ', '_')}.pdf"
                    ruta_tmp = os.path.join("/tmp", nombre_archivo)
                    
                    # Consolidar acciones formativas
                    acciones_texto = "\n".join(datos_empresa[col_accion].astype(str).tolist())
                    
                    # Campos a llenar (Asegúrate de que coincidan con tu PDF)
                    campos = {
                        'Empresa': empresa_sel,
                        'Acciones de Capacitación': acciones_texto,
                        'Dirección Regional': 'Cibao Norte'
                    }
                    
                    # 1. Crear el PDF físicamente en el servidor
                    fillpdfs.write_fillable_pdf(PLANTILLA, ruta_tmp, campos)
                    
                    # 2. Obtener carpeta en Drive
                    id_subcarpeta = obtener_o_crear_carpeta(empresa_sel)
                    
                    # 3. Subida con soporte de cuota compartida
                    meta_file = {'name': nombre_archivo, 'parents': [id_subcarpeta]}
                    media = MediaFileUpload(ruta_tmp, mimetype='application/pdf')
                    
                    drive_service.files().create(
                        body=meta_file, 
                        media_body=media, 
                        supportsAllDrives=True 
                    ).execute()
                    
                    st.success(f"✅ ¡Éxito! El cronograma de {empresa_sel} ha sido enviado a Drive.")
                    
            except Exception as e:
                st.error(f"❌ El error persiste: {e}")
