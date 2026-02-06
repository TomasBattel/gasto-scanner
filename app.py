import streamlit as st
import google.generativeai as genai
from PIL import Image
from pdf2image import convert_from_bytes
import json
import os

# Configuración de página
st.set_page_config(page_title="GastoScanner", page_icon="🧾")
st.title("🧾 GastoScanner (Modo Diagnóstico)")

# Configurar API
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("⚠️ Falta la API Key de Gemini.")
    st.stop()

genai.configure(api_key=api_key)

def analizar_ticket(image):
    # Intentamos primero con la versión específica 001 que suele ser más estable
    nombre_modelo = 'gemini-1.5-flash-001'
    model = genai.GenerativeModel(nombre_modelo)
    
    prompt = """
    Analiza este comprobante y extrae: fecha, monto, moneda (ARS/USD), descripcion, categoria, metodo_pago.
    Formato JSON.
    """
    
    with st.spinner(f'🤖 Intentando conectar con {nombre_modelo}...'):
        try:
            response = model.generate_content([prompt, image])
            text = response.text.replace('```json', '').replace('```', '').strip()
            return json.loads(text)
        except Exception as e:
            st.error(f"❌ Falló el modelo {nombre_modelo}.")
            
            # --- ZONA DE DIAGNÓSTICO ---
            st.warning("🔍 Iniciando diagnóstico de modelos disponibles...")
            try:
                available_models = []
                for m in genai.list_models():
                    if 'generateContent' in m.supported_generation_methods:
                        available_models.append(m.name)
                
                st.info(f"✅ Modelos encontrados para tu API Key:\n\n" + "\n".join(available_models))
            except Exception as e_diag:
                st.error(f"No pude ni listar los modelos: {e_diag}")
            # ---------------------------
            return None

# Interfaz
uploaded_file = st.file_uploader("Subí foto o PDF", type=["jpg", "png", "jpeg", "pdf"])

if uploaded_file is not None:
    if uploaded_file.type == "application/pdf":
        try:
            images = convert_from_bytes(uploaded_file.read())
            img = images[0]
            st.image(img, caption='PDF Página 1', use_column_width=True)
            uploaded_file.seek(0)
        except:
            st.error("Error leyendo PDF.")
            st.stop()
    else:
        img = Image.open(uploaded_file)
        st.image(img, caption='Imagen', use_column_width=True)

    if st.button("✨ Analizar con IA"):
        datos = analizar_ticket(img)
        if datos:
            st.success("¡Éxito! Datos extraídos:")
            st.json(datos)
