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
    st.error("⚠️ Falta la API Key de Gemini. Configurala en las variables de entorno.")
    st.stop()

genai.configure(api_key=api_key)

def analizar_ticket(image):
    """Envía la imagen al modelo Gemini 2.0 Flash"""
    # ACTUALIZACIÓN: Usamos el modelo que apareció en tu lista diagnóstica
    model = genai.GenerativeModel('gemini-2.0-flash')
    
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
    
    with st.spinner('🤖 Gemini 2.0 analizando el comprobante...'):
        try:
            response = model.generate_content([prompt, image])
            # Limpiar posible markdown ```json ... ```
            text = response.text.replace('```json', '').replace('```', '').strip()
            return json.loads(text)
        except Exception as e:
            st.error(f"Error al procesar: {e}")
            return None

# Interfaz de carga (Soporta PDF e Imágenes)
uploaded_file = st.file_uploader("Subí foto o PDF", type=["jpg", "png", "jpeg", "pdf"])

if uploaded_file is not None:
    col1, col2 = st.columns(2)
    
    # Variable para guardar la imagen que se enviará a la IA
    imagen_para_ia = None

    with col1:
        try:
            if uploaded_file.type == "application/pdf":
                # Convertir primera página del PDF a imagen
                images = convert_from_bytes(uploaded_file.read())
                if images:
                    imagen_para_ia = images[0]
                    st.info("📄 PDF detectado: Procesando la primera página.")
                    st.image(imagen_para_ia, caption='Vista previa PDF', use_column_width=True)
                    # Resetear puntero por si hiciera falta, aunque ya tenemos la imagen
                    uploaded_file.seek(0)
            else:
                # Es una imagen normal
                imagen_para_ia = Image.open(uploaded_file)
                st.image(imagen_para_ia, caption='Tu Comprobante', use_column_width=True)
        except Exception as e:
            st.error(f"Error al leer el archivo: {e}")
            st.stop()

    with col2:
        # Botón para procesar
        if st.button("✨ Analizar con IA", type="primary"):
            if imagen_para_ia:
                datos = analizar_ticket(imagen_para_ia)
                
                if datos:
                    st.success("¡Datos extraídos con Gemini 2.0!")
                    
                    # Formulario editable
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
                        
                        submitted = st.form_submit_button("💾 Guardar en Sheets")
                        
                        if submitted:
                            st.info("🚧 ¡Casi listo! Solo falta conectar la Google Sheet.")
                            st.json({
                                "Fecha": fecha,
                                "Monto": monto,
                                "Moneda": moneda,
                                "Descripcion": desc,
                                "Categoria": cat
                            })
