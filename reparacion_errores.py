import os
import json
import time
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

MODEL_NAME = 'models/gemini-flash-latest'
INVOICES_DIR = "Invoices"
OUTPUT_FILE = "Output/facturas_extraidas.json"

def esperar_archivo_activo(file):
    print(f"   ⏳ Subiendo...", end='', flush=True)
    while file.state.name == "PROCESSING":
        time.sleep(1)
        file = genai.get_file(file.name)
    if file.state.name != "ACTIVE":
        raise Exception("Fallo al procesar PDF")
    print(" Listo.")

def extraer_con_reintento(pdf_path, intentos=3):
    """Intenta extraer datos. Si falla por cuota (429), espera y reintenta."""
    for i in range(intentos):
        try:
            myfile = genai.upload_file(pdf_path)
            esperar_archivo_activo(myfile)
            
            prompt = """
            Extrae en JSON estricto:
            {
                "nombre_proveedor": "Texto",
                "nit_proveedor": "Solo números, SIN puntos/guiones/digito verificación",
                "numero_factura": "Texto",
                "fecha_emision": "YYYY-MM-DD",
                "subtotal": 0.0,
                "iva_monto": 0.0,
                "total": 0.0
            }
            """
            model = genai.GenerativeModel(MODEL_NAME)
            result = model.generate_content([myfile, prompt])
            texto = result.text.replace("```json", "").replace("```", "").strip()
            return json.loads(texto)
            
        except Exception as e:
            if "429" in str(e) or "Quota" in str(e):
                tiempo_espera = 60 # Esperar 1 Min
                print(f"Límite alcanzado. Esperando {tiempo_espera}seg para reintentar... (Intento {i+1}/{intentos})")
                time.sleep(tiempo_espera)
            else:
                print(f"Error desconocido: {e}")
                return None
    return None

def main():
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            datos_existentes = json.load(f)
    else:
        datos_existentes = []

    # Crear lista de archivos ya procesados exitosamente
    procesados_ok = {d['nombre_archivo'] for d in datos_existentes if 'error' not in d}
    
    archivos = [f for f in os.listdir(INVOICES_DIR) if f.lower().endswith(".pdf")]
    faltantes = [f for f in archivos if f not in procesados_ok]

    print(f"Estado actual: {len(procesados_ok)} listas, {len(faltantes)} fallaron o faltan.")
    
    if not faltantes:
        print("Todo está completo! No hay nada que reparar.")
        return

    print(f"Iniciando reparación de {len(faltantes)} facturas...")

    nuevos_datos = []
    
    for archivo in faltantes:
        print(f"Reparando: {archivo}...")
        ruta = os.path.join(INVOICES_DIR, archivo)
        
        datos = extraer_con_reintento(ruta)
        
        if datos:
            datos['nombre_archivo'] = archivo
            nuevos_datos.append(datos)
            print(f"Recuperado: {datos.get('nit_proveedor', 'Sin NIT')}")
        else:
            print("No se pudo recuperar.")
            nuevos_datos.append({"nombre_archivo": archivo, "error": "Fallo persistente"})
        
        time.sleep(10) 

    # Combinar y guardar
    datos_limpios = [d for d in datos_existentes if d['nombre_archivo'] not in [n['nombre_archivo'] for n in nuevos_datos]]
    datos_finales = datos_limpios + nuevos_datos
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(datos_finales, f, indent=4, ensure_ascii=False)

    print(f"\nReparación terminada{OUTPUT_FILE}")

if __name__ == "__main__":
    main()