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

if not creds_sheets:
    st.warning("⚠️ ATENCIÓN: Falta la variable `GOOGLE_SHEETS_CREDENTIALS`. Podrás escanear, pero NO guardar.")

genai.configure(api_key=api_key)

# --- FUNCIONES ---
def analizar_ticket(image):
    """Analiza la imagen usando el mejor modelo disponible."""
    # Selección de modelo "todo terreno"
    modelo_nombre = 'gemini-1.5-flash' # Default
    try:
        # Intentamos buscar si hay uno mejor disponible (ej: 1.5 Pro o 2.0 experimental)
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if 'gemini-1.5-flash' in m.name: modelo_nombre = m.name
    except Exception as e:
        st.warning(f"No pude listar modelos, usando {modelo_nombre} por defecto. Error: {e}")

    model = genai.GenerativeModel(modelo_nombre)
    
    prompt = """
    Analiza este comprobante de pago. Responde SOLO con un JSON válido.
    Estructura: {"fecha": "DD/MM/YYYY", "monto": 0.00, "moneda": "ARS", "descripcion": "Texto", "categoria": "Otros", "metodo_pago": "Efectivo"}
    Si no encuentras un dato, pon null.
    """
    
    try:
        with st.spinner(f"🧠 Analizando con {modelo_nombre}..."):
            response = model.generate_content([prompt, image])
            # Limpieza quirúrgica del JSON
            texto_limpio = response.text.replace('```json', '').replace('```', '').strip()
            return json.loads(texto_limpio)
    except Exception as e:
        st.error(f"❌ Error en la IA: {str(e)}")
        return None

def guardar_en_sheets(datos):
    """Guarda los datos en la hoja de cálculo."""
    if not creds_sheets:
        st.error("No hay credenciales configuradas en Coolify.")
        return False
        
    try:
        creds_dict = json.loads(creds_sheets)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # IMPORTANTE: Cambiá "Control de Gastos" por el nombre REAL de tu archivo si es distinto
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

# --- INTERFAZ CON MEMORIA (SESSION STATE) ---
if 'datos_ticket' not in st.session_state:
    st.session_state.datos_ticket = None

uploaded_file = st.file_uploader("Subí tu comprobante", type=["jpg", "png", "jpeg", "pdf"])

if uploaded_file:
    # Mostrar imagen
    if uploaded_file.type == "application/pdf":
        images = convert_from_bytes(uploaded_file.read())
        img_show = images[0]
        st.image(img_show, caption='PDF Página 1', width=300)
        uploaded_file.seek(0)
    else:
        img_show = Image.open(uploaded_file)
        st.image(img_show, caption='Comprobante', width=300)

    # Botón de Análisis
    if st.button("✨ Analizar Recibo", type="primary"):
        resultado = analizar_ticket(img_show)
        if resultado:
            st.session_state.datos_ticket = resultado # Guardamos en memoria
            st.rerun() # Recargamos para mostrar el formulario

# Si hay datos en memoria, mostramos el formulario de guardado
if st.session_state.datos_ticket:
    st.divider()
    st.success("✅ ¡Información extraída!")
    
    with st.form("form_guardado"):
        col1, col2 = st.columns(2)
        d = st.session_state.datos_ticket
        
        fecha = col1.text_input("Fecha", value=d.get("fecha") or "")
        monto = col2.number_input("Monto", value=float(d.get("monto") or 0))
        moneda = col1.selectbox("Moneda", ["ARS", "USD"], index=0 if d.get("moneda") == "ARS" else 1)
        categoria = col2.selectbox("Categoría", ["Comida", "Servicios", "Supermercado", "Transporte", "Otros"], index=4)
        desc = st.text_input("Descripción", value=d.get("descripcion") or "")
        pago = st.selectbox("Método Pago", ["Efectivo", "Debito", "Credito", "MP", "Transferencia"], index=4)
        
        submitted = st.form_submit_button("💾 Guardar en Google Sheets")
        
        if submitted:
            datos_finales = {
                "fecha": fecha, "monto": monto, "moneda": moneda,
                "categoria": categoria, "descripcion": desc, "metodo_pago": pago
            }
            if guardar_en_sheets(datos_finales):
                st.balloons()
                st.success("Guardado exitosamente.")
                st.session_state.datos_ticket = None # Limpiar memoria
            else:
                st.error("Falló el guardado. Revisá los logs.")
