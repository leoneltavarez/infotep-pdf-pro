import streamlit as st
import pandas as pd
import fillpdf
from fillpdf import fillpdfs
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# 1. CONFIGURACIÓN DE SEGURIDAD
creds_info = json.loads(st.secrets["google_creds"]["json_data"])
creds = service_account.Credentials.from_service_account_info(creds_info)
drive_service = build('drive', 'v3', credentials=creds)

PARENT_FOLDER_ID = "1X-dNqrDVubLCqZyLh2rzHWFhZb47R0-m"
PLANTILLA = "PLANTILLA_FINAL.pdf"

# Función para organizar por empresas
def get_or_create_folder(folder_name):
    query = f"name = '{folder_name}' and '{PARENT_FOLDER_ID}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = drive_service.files().list(q=query).execute().get('files', [])
    if results:
        return results[0]['id']
    folder_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [PARENT_FOLDER_ID]}
    file = drive_service.files().create(body=folder_metadata, fields='id').execute()
    return file.get('id')

st.title("Generador Pro - INFOTEP 2026")

# 2. SELECCIÓN DE EMPRESA (Asegúrate de que tus datos carguen aquí)
# empresa_seleccionada = st.selectbox("Seleccione la Empresa", lista_empresas)

if st.button("Generar y Enviar a Drive"):
    if not os.path.exists(PLANTILLA):
        st.error("❌ Error Crítico: No se encuentra PLANTILLA_FINAL.pdf en el repositorio de GitHub.")
    else:
        try:
            # Definir nombres y rutas
            empresa = "COBB CARIBE S A" # Aquí usarás la variable del selectbox
            nombre_archivo = f"Cronograma_{empresa.replace(' ', '_')}.pdf"
            ruta_temporal = os.path.join("/tmp", nombre_archivo) # FORZAMOS ESCRITURA EN TMP

            # PASO A: Llenado del PDF
            # Ajusta los nombres de los campos ('Empresa', etc.) a los que usas en tu laptop
            datos_llenado = {'Empresa': empresa, 'Dirección Regional': 'Cibao Norte'} 
            
            fillpdfs.write_fillable_pdf(PLANTILLA, ruta_temporal, datos_llenado)

            # PASO B: Crear/Obtener carpeta en Drive
            id_carpeta_destino = get_or_create_folder(empresa)

            # PASO C: Subida a Drive
            file_metadata = {'name': nombre_archivo, 'parents': [id_carpeta_destino]}
            media = MediaFileUpload(ruta_temporal, mimetype='application/pdf')
            drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

            st.success(f"✅ ¡ÉXITO! El cronograma de {empresa} se guardó en su carpeta correspondiente en Drive.")
            
        except Exception as e:
            st.error(f"Fallo en el sistema: {str(e)}")
