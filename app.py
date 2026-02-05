import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import os
from datetime import datetime

# Configuración de página
st.set_page_config(page_title="GastoScanner", page_icon="🧾")

# Título y estilos
st.title("🧾 GastoScanner")
st.markdown("Subí tu comprobante para procesarlo con IA.")

# Configurar API de Gemini desde variable de entorno
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("⚠️ Falta la API Key de Gemini. Configurala en las variables de entorno.")
    st.stop()

genai.configure(api_key=api_key)

def analizar_ticket(image):
    """Envía la imagen a Gemini Flash y pide un JSON estructurado"""
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Prompt optimizado para tus gastos
    prompt = """
    Analiza este comprobante de pago y extrae la siguiente información en formato JSON puro (sin markdown).
    Si algún dato no aparece, usa null o intenta inferirlo por el contexto (ej: si es una hamburguesa, categoría: Comida).
    
    Estructura requerida:
    {
        "fecha": "DD/MM/YYYY",
        "monto": 0.00 (número decimal),
        "moneda": "ARS" o "USD",
        "descripcion": "Breve descripción del ítem/comercio",
        "categoria": "Sugerir una (Comida, Servicios, Supermercado, Transporte, Otros)",
        "metodo_pago": "Detectar si dice Visa, Mastercard, MercadoPago, etc."
    }
    """
    
    with st.spinner('🤖 Gemini está leyendo el ticket...'):
        response = model.generate_content([prompt, image])
        try:
            # Limpiar posible markdown ```json ... ```
            text = response.text.replace('```json', '').replace('```', '').strip()
            return json.loads(text)
        except:
            st.error("No pude entender la respuesta de la IA. Intentá de nuevo.")
            return None

# Interfaz de carga
uploaded_file = st.file_uploader("Elegí una foto o sacá una ahora", type=["jpg", "png", "jpeg"])

if uploaded_file is not None:
    col1, col2 = st.columns(2)
    
    with col1:
        st.image(uploaded_file, caption='Tu Comprobante', use_column_width=True)
        img = Image.open(uploaded_file)
    
    with col2:
        # Botón para procesar
        if st.button("✨ Analizar con IA", type="primary"):
            datos = analizar_ticket(img)
            
            if datos:
                st.success("¡Datos extraídos!")
                
                # Formulario editable por si la IA pifia en algo
                with st.form("edit_form"):
                    fecha = st.text_input("Fecha", value=datos.get("fecha"))
                    monto = st.number_input("Monto", value=datos.get("monto"))
                    moneda = st.selectbox("Moneda", ["ARS", "USD"], index=0 if datos.get("moneda") == "ARS" else 1)
                    desc = st.text_input("Descripción", value=datos.get("descripcion"))
                    cat = st.selectbox("Categoría", ["Comida", "Servicios", "Supermercado", "Transporte", "Otros"], index=0) # Acá podés ajustar tus categorías reales
                    
                    submitted = st.form_submit_button("💾 Guardar en Sheets")
                    
                    if submitted:
                        st.info("🚧 Acá conectaremos con Google Sheets en el próximo paso.")
                        st.json({
                            "Fecha": fecha,
                            "Monto": monto,
                            "Moneda": moneda,
                            "Descripcion": desc,
                            "Categoria": cat
                        })
