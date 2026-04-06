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

# IDs de Referencia
PARENT_FOLDER_ID = "1X-dNqrDVubLCqZyLh2rzHWFhZb47R0-m"
PLANTILLA = "PLANTILLA_FINAL.pdf"

# --- 3. MOTOR DE DATOS (GOOGLE SHEETS) ---
@st.cache_data
def cargar_datos():
    sheet_id = "1SiA8b7PAWOlTUfrHu_ew3Qt-D1JTVSZKQ8bUbSS4GQU"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    data = pd.read_csv(url)
    # Normalizar nombres de columnas (Mayúsculas y sin espacios)
    data.columns = [str(c).strip().upper() for c in data.columns]
    return data

try:
    df = cargar_datos()
    col_empresa = [c for c in df.columns if 'EMPRESA' in c][0]
    lista_empresas = sorted(df[col_empresa].dropna().unique())
    empresa_sel = st.selectbox("🎯 Seleccione la Empresa:", lista_empresas)
except Exception as e:
    st.error(f"❌ Error al cargar Excel: {e}")
    df = None

# --- 4. FUNCIONES DE DRIVE (CON CORRECCIÓN DE CUOTA) ---
def obtener_o_crear_carpeta(nombre_carpeta):
    query = f"name = '{nombre_carpeta}' and '{PARENT_FOLDER_ID}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    # Usamos supportsAllDrives para que el robot pueda ver carpetas compartidas
    respuesta = drive_service.files().list(q=query, supportsAllDrives=True, includeItemsFromAllDrives=True).execute().get('files', [])
    
    if respuesta:
        return respuesta[0]['id']
    
    meta = {
        'name': nombre_carpeta, 
        'mimeType': 'application/vnd.google-apps.folder', 
        'parents': [PARENT_FOLDER_ID]
    }
    return drive_service.files().create(body=meta, fields='id', supportsAllDrives=True).execute().get('id')

# --- 5. EJECUCIÓN ---
if st.button("🛠️ Generar Cronograma y Subir a Drive"):
    if df is not None:
        if not os.path.exists(PLANTILLA):
            st.error(f"❌ No se encontró {PLANTILLA} en el repositorio de GitHub.")
        else:
            try:
                with st.spinner(f"Procesando {empresa_sel}..."):
                    # Buscar columna de acciones formativas
                    col_accion = [c for c in df.columns if 'ACCION' in c or 'FORMATIVA' in c][0]
                    datos_empresa = df[df[col_empresa] == empresa_sel]
                    
                    # Ruta temporal para la nube
                    nombre_archivo = f"Cronograma_{empresa_sel.replace(' ', '_')}.pdf"
                    ruta_tmp = os.path.join("/tmp", nombre_archivo)
                    
                    # Consolidar las acciones formativas en un solo bloque de texto
                    acciones_texto = "\n".join(datos_empresa[col_accion].astype(str).tolist())
                    
                    # Mapear datos a los campos del PDF (Ajusta los nombres a tu plantilla)
                    campos = {
                        'Empresa': empresa_sel,
                        'Dirección Regional': 'Cibao Norte',
                        'Acciones de Capacitación': acciones_texto
                    }
                    
                    # 1. Generar el PDF
                    fillpdfs.write_fillable_pdf(PLANTILLA, ruta_tmp, campos)
                    
                    # 2. Asegurar carpeta en Drive
                    id_subcarpeta = obtener_o_crear_carpeta(empresa_sel)
                    
                    # 3. Subir archivo final (supportsAllDrives resuelve el error de cuota)
                    meta_file = {'name': nombre_archivo, 'parents': [id_subcarpeta]}
                    media = MediaFileUpload(ruta_tmp, mimetype='application/pdf')
                    drive_service.files().create(
                        body=meta_file, 
                        media_body=media, 
                        supportsAllDrives=True
                    ).execute()
                    
                    st.success(f"✅ ¡Éxito! El cronograma de {empresa_sel} con sus {len(datos_empresa)} acciones ya está en Drive.")
            except Exception as e:
                st.error(f"❌ Fallo en el motor: {e}")
