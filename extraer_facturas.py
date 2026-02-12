import os
import json
import time
import google.generativeai as genai
from dotenv import load_dotenv

#Configuración
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    raise ValueError("No se encontró la API Key en el archivo .env")

genai.configure(api_key=api_key)

MODEL_NAME = 'models/gemini-flash-latest'

# Carpetas
INVOICES_DIR = "Invoices"
OUTPUT_FILE = "Output/facturas_extraidas.json"

def esperar_archivo_activo(file):
    """Espera a que Google procese el archivo PDF"""
    print(f" Procesando PDF en la nube...", end='', flush=True)
    while file.state.name == "PROCESSING":
        print(".", end='', flush=True)
        time.sleep(1)
        file = genai.get_file(file.name)
    
    if file.state.name != "ACTIVE":
        raise Exception(f"El archivo {file.uri} falló.")
    print(" ¡Listo!")

def extraer_datos_factura(pdf_path):
    print(f"Leyendo: {os.path.basename(pdf_path)}...")
    
    # Subir el archivo 
    myfile = genai.upload_file(pdf_path)
    esperar_archivo_activo(myfile)

    # El Prompt
    prompt = """
    Actúa como un experto en extracción de datos contables. Analiza esta factura y extrae la siguiente información en formato JSON estricto.
    
    REGLAS DE EXTRACCIÓN:
    1. nit_proveedor: Solo números. ELIMINA puntos, guiones, espacios, prefijos 'CO' y el dígito de verificación si está separado por guion. (Ejemplo: Si ves 900.123.456-1, extrae "900123456").
    2. nombre_proveedor: Nombre de la empresa o persona.
    3. numero_factura: El ID o folio de la factura.
    4. fecha_emision: Formato YYYY-MM-DD.
    5. total: El monto total a pagar (número, sin símbolos de moneda).
    6. subtotal: El monto antes de impuestos.
    7. iva_monto: El monto del impuesto IVA.

    Responde SOLO con el JSON, sin bloques de código ```json``` ni explicaciones adicionales.
    
    Estructura esperada:
    {
        "nombre_proveedor": "Texto",
        "nit_proveedor": "Texto",
        "numero_factura": "Texto",
        "fecha_emision": "YYYY-MM-DD",
        "subtotal": 0.0,
        "iva_monto": 0.0,
        "total": 0.0
    }
    """

    model = genai.GenerativeModel(MODEL_NAME)
    result = model.generate_content([myfile, prompt])
    
    # Limpiamos la respuesta 
    texto_limpio = result.text.replace("```json", "").replace("```", "").strip()
    
    try:
        data = json.loads(texto_limpio)
        # Agregar el nombre de archivo para referencia
        data["nombre_archivo"] = os.path.basename(pdf_path)
        return data
    except json.JSONDecodeError:
        print(f"No devolvió un JSON válido para {pdf_path}")
        return {"nombre_archivo": os.path.basename(pdf_path), "error": "Formato inválido"}

def main():
    # Asegurar que existe la carpeta de salida
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    # Verificar que existan facturas
    if not os.path.exists(INVOICES_DIR):
        print(f"No existe la carpeta '{INVOICES_DIR}'.")
        return

    archivos = [f for f in os.listdir(INVOICES_DIR) if f.lower().endswith(".pdf")]
    
    if not archivos:
        print(f" Error en la carpeta '{INVOICES_DIR}' está vacía.")
        return

    print(f"Inicio de extracción de {len(archivos)} facturas...")
    facturas_procesadas = []

    for i, archivo in enumerate(archivos):
        ruta_pdf = os.path.join(INVOICES_DIR, archivo)
        try:
            datos = extraer_datos_factura(ruta_pdf)
            facturas_procesadas.append(datos)
        
            if "nit_proveedor" in datos:
                print(f"Nit Exito: {datos['nit_proveedor']} | Total: {datos['total']}")
            
        except Exception as e:
            print(f"Error en {archivo}: {e}")
            facturas_procesadas.append({"nombre_archivo": archivo, "error": str(e)})
        
        time.sleep(2)

    # Guarda el JSON 
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(facturas_procesadas, f, indent=4, ensure_ascii=False)
    
    print(f"\nDatos guardados en {OUTPUT_FILE}")

if __name__ == "__main__":
    main()