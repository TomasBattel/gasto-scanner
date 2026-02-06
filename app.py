import streamlit as st
import google.generativeai as genai
from PIL import Image
from pdf2image import convert_from_bytes
import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="GastoScanner Pro", page_icon="🧾")
st.title("🧾 GastoScanner Pro")

# Verificar API Keys al inicio
api_key = os.getenv("GEMINI_API_KEY")
creds_sheets = os.getenv("GOOGLE_SHEETS_CREDENTIALS")

if not api_key:
    st.error("❌ ERROR CRÍTICO: Falta la variable `GEMINI_API_KEY`.")
    st.stop()

# Advertencia si falta Sheets, pero deja seguir
if not creds_sheets:
    st.warning("⚠️ Falta `GOOGLE_SHEETS_CREDENTIALS`. Podrás escanear, pero NO guardar.")

genai.configure(api_key=api_key)

# --- FUNCIONES ---
def conseguir_nombre_modelo():
    """Busca el mejor modelo disponible, priorizando los nuevos gratuitos."""
    try:
        modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # Lista de prioridad: buscamos del más nuevo/potente gratis al más viejo
        preferencias = [
            'gemini-2.5-flash', # El que te funcionó antes
            'gemini-2.0-flash-exp',
            'gemini-1.5-pro-latest',
            'gemini-1.5-flash-latest',
            'gemini-1.5-flash'
        ]
        
        # Devuelve el primero de la lista de preferencias que exista en tu cuenta
        for pref in preferencias:
            for m in modelos:
                if pref in m: return m
                
        # Si no encuentra ninguno de los preferidos, devuelve el primero que haya
        if modelos: return modelos[0]
        
    except:
        pass
    # Último recurso si todo falla
    return 'gemini-1.5-flash'

def analizar_ticket(image):
    # Usamos el "detective" para elegir el modelo
    modelo_nombre = conseguir_nombre_modelo()
    model = genai.GenerativeModel(modelo_nombre)
    
    prompt = """
    Analiza este comprobante de pago. Responde SOLO con un JSON válido.
    Estructura: {"fecha": "DD/MM/YYYY", "monto": 0.00, "moneda": "ARS", "descripcion": "Texto", "categoria": "Otros", "metodo_pago": "Efectivo"}
    Si no encuentras un dato, pon null.
    Use punto para decimales.
    """
    
    try:
        with st.spinner(f"🧠 Analizando con {modelo_nombre}..."):
            response = model.generate_content([prompt, image])
            texto_limpio = response.text.replace('```json', '').replace('```', '').strip()
            return json.loads(texto_limpio)
    except Exception as e:
        st.error(f"❌ Error en la IA ({modelo_nombre}): {str(e)}")
        return None

def guardar_en_sheets(datos):
    if not creds_sheets:
        st.error("No hay credenciales de Sheets configuradas.")
        return False
    try:
        creds_dict = json.loads(creds_sheets)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # *** ASEGURATE QUE ESTE NOMBRE SEA CORRECTO ***
        sheet = client.open("Control de Gastos").worksheet("Gastos Mensuales")
        
        fila = [
            datos.get("fecha", ""),
            datos.get("categoria", "Otros"),
            datos.get("monto", 0),
            datos.get("moneda", "ARS"),
            datos.get("descripcion", ""),
            datos.get("metodo_pago", "")
        ]
        sheet.append_row(fila)
        return True
    except Exception as e:
        st.error(f"❌ Error al guardar en Excel: {str(e)}")
        return False

# --- INTERFAZ CON MEMORIA ---
if 'datos_ticket' not in st.session_state:
    st.session_state.datos_ticket = None

uploaded_file = st.file_uploader("Subí tu comprobante", type=["jpg", "png", "jpeg", "pdf"])

if uploaded_file:
    if uploaded_file.type == "application/pdf":
        images = convert_from_bytes(uploaded_file.read())
        img_show = images[0]
        st.image(img_show, caption='PDF', width=300)
        uploaded_file.seek(0)
    else:
        img_show = Image.open(uploaded_file)
        st.image(img_show, caption='Comprobante', width=300)

    if st.button("✨ Analizar Recibo", type="primary"):
        resultado = analizar_ticket(img_show)
        if resultado:
            st.session_state.datos_ticket = resultado
            st.rerun()

# Formulario de guardado (solo si hay datos en memoria)
if st.session_state.datos_ticket:
    st.divider()
    st.success("✅ Ticket leído. Revisá y guardá.")
    
    with st.form("form_guardado"):
        col1, col2 = st.columns(2)
        d = st.session_state.datos_ticket
        
        # Manejo seguro de valores nulos para evitar errores en los inputs
        fecha_val = d.get("fecha") if d.get("fecha") else ""
        monto_val = float(d.get("monto")) if d.get("monto") else 0.0
        desc_val = d.get("descripcion") if d.get("descripcion") else ""

        fecha = col1.text_input("Fecha", value=fecha_val)
        monto = col2.number_input("Monto ($)", value=monto_val, format="%.2f")
        moneda = col1.selectbox("Moneda", ["ARS", "USD"], index=0 if d.get("moneda") == "ARS" else 1)
        categoria = col2.selectbox("Categoría", ["Comida", "Servicios", "Supermercado", "Transporte", "Otros"], index=4)
        desc = st.text_input("Descripción", value=desc_val)
        pago = st.selectbox("Método Pago", ["Efectivo", "Debito", "Credito", "MP", "Transferencia"], index=1)
        
        submitted = st.form_submit_button("💾 Guardar en Google Sheets")
        
        if submitted
