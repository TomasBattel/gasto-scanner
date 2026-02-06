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

def conseguir_mejor_modelo():
    """Busca automáticamente qué modelo gratuito está disponible en tu cuenta"""
    try:
        st.toast("🔍 Buscando modelos disponibles...", icon="🤖")
        modelos_disponibles = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                modelos_disponibles.append(m.name)
        
        # Lógica de prioridad: Buscamos el mejor modelo GRATUITO disponible
        # 1. Gemini 1.5 Flash (El ideal)
        for m in modelos_disponibles:
            if 'gemini-1.5-flash' in m and '8b' not in m: return m
        
        # 2. Gemini 1.5 Pro (Si tenés suerte y está gratis)
        for m in modelos_disponibles:
            if 'gemini-1.5-pro' in m: return m
            
        # 3. Gemini Pro Vision (Versión anterior pero sirve)
        for m in modelos_disponibles:
            if 'vision' in m: return m

        # 4. Lo que sea que haya
        if modelos_disponibles: return modelos_disponibles[0]
        
        return None
    except Exception as e:
        st.error(f"Error buscando modelos: {e}")
        return None

# Inicializamos el modelo una sola vez
if "nombre_modelo" not in st.session_state:
    st.session_state.nombre_modelo = conseguir_mejor_modelo()

if not st.session_state.nombre_modelo:
    st.error("❌ No encontré ningún modelo disponible en tu cuenta. Chequeá tu API Key.")
    st.stop()

# Mostramos qué modelo eligió (para que sepas)
st.caption(f"✅ Usando modelo: `{st.session_state.nombre_modelo}`")

def analizar_ticket(image):
    model = genai.GenerativeModel(st.session_state.nombre_modelo)
    
    prompt = """
    Analiza este comprobante de pago y extrae la siguiente información en formato JSON puro.
    Si algún dato no aparece, usa null.
    
    Estructura JSON:
    {
        "fecha": "DD/MM/YYYY",
        "monto": 0.00,
        "moneda": "ARS" o "USD",
        "descripcion": "Texto breve",
        "categoria": "Comida, Servicios, Supermercado, Transporte, Otros",
        "metodo_pago": "Visa, Efectivo, MP, etc."
    }
    """
    
    with st.spinner(f'🤖 Procesando con {st.session_state.nombre_modelo}...'):
        try:
            response = model.generate_content([prompt, image])
            text = response.text.replace('```json', '').replace('```', '').strip()
            return json.loads(text)
        except Exception as e:
            st.error(f"Error al procesar: {e}")
            return None

# Interfaz de carga
uploaded_file = st.file_uploader("Subí foto o PDF", type=["jpg", "png", "jpeg", "pdf"])

if uploaded_file is not None:
    col1, col2 = st.columns(2)
    imagen_para_ia = None

    with col1:
        try:
            if uploaded_file.type == "application/pdf":
                images = convert_from_bytes(uploaded_file.read())
                if images:
                    imagen_para_ia = images[0]
                    st.info("📄 PDF detectado.")
                    st.image(imagen_para_ia, caption='Vista previa', use_column_width=True)
                    uploaded_file.seek(0)
            else:
                imagen_para_ia = Image.open(uploaded_file)
                st.image(imagen_para_ia, caption='Tu Comprobante', use_column_width=True)
        except Exception as e:
            st.error(f"Error archivo: {e}")

    with col2:
        if st.button("✨ Analizar con IA", type="primary"):
            if imagen_para_ia:
                datos = analizar_ticket(imagen_para_ia)
                if datos:
                    st.success("¡Datos extraídos!")
                    with st.form("edit_form"):
                        fecha = st.text_input("Fecha", value=datos.get("fecha"))
                        monto = st.number_input("Monto", value=datos.get("monto"))
                        
                        idx_moneda = 0
                        if datos.get("moneda") == "USD": idx_moneda = 1
                        moneda = st.selectbox("Moneda", ["ARS", "USD"], index=idx_moneda)
                        
                        desc = st.text_input("Descripción", value=datos.get("descripcion"))
                        
                        cats = ["Comida", "Servicios", "Supermercado", "Transporte", "Otros"]
                        cat_val = datos.get("categoria", "Otros")
                        idx_cat = cats.index(cat_val) if cat_val in cats else 4
                        cat = st.selectbox("Categoría", cats, index=idx_cat)
                        
                        if st.form_submit_button("💾 Guardar en Sheets"):
                            st.info("🚧 Conexión a Sheets pendiente.")
                            st.json(datos)
