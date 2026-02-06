import streamlit as st
import google.generativeai as genai
from PIL import Image
from pdf2image import convert_from_bytes
import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Configuración de página
st.set_page_config(page_title="GastoScanner", page_icon="🧾")
st.title("🧾 GastoScanner")

# --- CONFIGURACIÓN GEMINI ---
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("⚠️ Falta GEMINI_API_KEY.")
    st.stop()

genai.configure(api_key=api_key)

# --- CONFIGURACIÓN GOOGLE SHEETS ---
def guardar_en_sheets(datos):
    """Conecta con Google Sheets y guarda la fila"""
    try:
        # Leemos el JSON de credenciales desde la variable de entorno
        creds_json_str = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
        if not creds_json_str:
            st.error("❌ Falta la variable GOOGLE_SHEETS_CREDENTIALS en Coolify.")
            return False

        # Parseamos el string JSON a un diccionario
        creds_dict = json.loads(creds_json_str)
        
        # Definimos el alcance
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # Autenticación
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # Abrir la hoja de cálculo.
        # IMPORTANTE: Asegurate que el nombre sea EXACTO al de tu archivo en Drive
        sheet = client.open("Control de Gastos").worksheet("Gastos Mensuales")
        
        # Preparar la fila. El orden DEBE COINCIDIR con tus columnas en el Excel.
        # Ejemplo: Fecha, Categoría, Monto, Moneda, Descripción, Metodo Pago
        # Ajustá este orden según tu planilla real.
        fila = [
            datos.get("fecha", ""),
            datos.get("categoria", ""),
            datos.get("monto", 0),
            datos.get("moneda", "ARS"),
            datos.get("descripcion", ""),
            datos.get("metodo_pago", "")
        ]
        
        sheet.append_row(fila)
        return True
        
    except Exception as e:
        st.error(f"Error guardando en Sheets: {e}")
        return False

# --- LÓGICA DE IA ---
def analizar_ticket(image):
    # Buscamos modelo disponible
    modelo_usar = 'gemini-1.5-flash' # Default seguro
    try:
        for m in genai.list_models():
             if 'gemini-1.5-flash' in m.name and '8b' not in m.name: modelo_usar = m.name
    except: pass
    
    model = genai.GenerativeModel(modelo_usar)
    
    prompt = """
    Analiza este comprobante. Extrae JSON:
    {
        "fecha": "DD/MM/YYYY",
        "monto": 0.00,
        "moneda": "ARS" o "USD",
        "descripcion": "Texto breve",
        "categoria": "Comida, Servicios, Supermercado, Transporte, Otros",
        "metodo_pago": "Efectivo, Debito, Credito, MP"
    }
    """
    with st.spinner(f'🤖 Procesando...'):
        try:
            response = model.generate_content([prompt, image])
            text = response.text.replace('```json', '').replace('```', '').strip()
            return json.loads(text)
        except: return None

# --- INTERFAZ ---
uploaded_file = st.file_uploader("Subí comprobante", type=["jpg", "png", "jpeg", "pdf"])

if uploaded_file is not None:
    # (Lógica de visualización igual que antes...)
    if uploaded_file.type == "application/pdf":
        images = convert_from_bytes(uploaded_file.read())
        img = images[0]
        st.image(img, caption='PDF', use_column_width=True)
        uploaded_file.seek(0)
    else:
        img = Image.open(uploaded_file)
        st.image(img, caption='Imagen', use_column_width=True)

    if st.button("✨ Analizar", type="primary"):
        datos = analizar_ticket(img)
        if datos:
            st.success("¡Leído!")
            with st.form("save_form"):
                # Campos editables
                col_a, col_b = st.columns(2)
                fecha = col_a.text_input("Fecha", datos.get("fecha"))
                monto = col_b.number_input("Monto", value=float(datos.get("monto") or 0))
                
                cat = st.selectbox("Categoría", ["Comida", "Servicios", "Supermercado", "Transporte", "Otros"], index=0)
                desc = st.text_input("Descripción", datos.get("descripcion"))
                metodo = st.selectbox("Pago", ["Efectivo", "Debito", "Credito", "MP"], index=1)
                
                submitted = st.form_submit_button("💾 Guardar en Google Sheets")
                
                if submitted:
                    datos_finales = {
                        "fecha": fecha, "monto": monto, "moneda": datos.get("moneda"), 
                        "categoria": cat, "descripcion": desc, "metodo_pago": metodo
                    }
                    if guardar_en_sheets(datos_finales):
                        st.balloons()
                        st.success("✅ ¡Guardado en tu Excel!")
                    else:
                        st.error("Hubo un error al guardar.")
