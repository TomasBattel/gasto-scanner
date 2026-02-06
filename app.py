import streamlit as st
import google.generativeai as genai
from PIL import Image
from pdf2image import convert_from_bytes
import json
import os

# Configuración de página
st.set_page_config(page_title="GastoScanner", page_icon="🧾")

st.title("🧾 GastoScanner")
st.markdown("Subí tu comprobante (Foto o PDF) para procesarlo con IA.")

# Configurar API
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("⚠️ Falta la API Key de Gemini.")
    st.stop()

genai.configure(api_key=api_key)

def analizar_ticket(image):
    """Envía la imagen a Gemini Flash"""
    # Usamos el nombre estándar. Con la librería actualizada en requirements.txt esto FUNCIONA.
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = """
    Analiza este comprobante de pago y extrae la siguiente información en formato JSON puro (sin markdown).
    Si algún dato no aparece, usa null o intenta inferirlo por el contexto.
    
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
    
    with st.spinner('🤖 Gemini está leyendo el comprobante...'):
        try:
            response = model.generate_content([prompt, image])
            text = response.text.replace('```json', '').replace('```', '').strip()
            return json.loads(text)
        except Exception as e:
            st.error(f"Error al procesar: {e}")
            return None

# Interfaz de carga (ahora acepta PDF)
uploaded_file = st.file_uploader("Subí foto o PDF", type=["jpg", "png", "jpeg", "pdf"])

if uploaded_file is not None:
    col1, col2 = st.columns(2)
    
    with col1:
        # Lógica para mostrar la imagen previa
        try:
            if uploaded_file.type == "application/pdf":
                # Convertir primera página del PDF a imagen
                images = convert_from_bytes(uploaded_file.read())
                img = images[0]
                st.info("📄 PDF detectado: Procesando la primera página.")
                st.image(img, caption='Vista previa PDF', use_column_width=True)
                # Volvemos al inicio del archivo por si acaso
                uploaded_file.seek(0) 
            else:
                # Es una imagen normal
                img = Image.open(uploaded_file)
                st.image(uploaded_file, caption='Tu Comprobante', use_column_width=True)
        except Exception as e:
            st.error("Error al leer el archivo. Asegurate de que no esté dañado.")
            st.stop()

    with col2:
        if st.button("✨ Analizar con IA", type="primary"):
            datos = analizar_ticket(img)
            
            if datos:
                st.success("¡Datos extraídos!")
                
                with st.form("edit_form"):
                    fecha = st.text_input("Fecha", value=datos.get("fecha"))
                    monto = st.number_input("Monto", value=datos.get("monto"))
                    
                    idx_moneda = 0
                    if datos.get("moneda") == "USD": idx_moneda = 1
                    moneda = st.selectbox("Moneda", ["ARS", "USD"], index=idx_moneda)
                    
                    desc = st.text_input("Descripción", value=datos.get("descripcion"))
                    
                    categorias = ["Comida", "Servicios", "Supermercado", "Transporte", "Otros"]
                    cat_val = datos.get("categoria", "Otros")
                    idx_cat = 0
                    if cat_val in categorias: idx_cat = categorias.index(cat_val)
                    cat = st.selectbox("Categoría", categorias, index=idx_cat)
                    
                    if st.form_submit_button("💾 Guardar en Sheets"):
                        st.info("🚧 Acá conectaremos con Google Sheets en el próximo paso.")
                        st.json(datos)
