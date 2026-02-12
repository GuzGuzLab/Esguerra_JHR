import pandas as pd
import json
import os
import matplotlib.pyplot as plt

# Archivos
JSON_FACTURAS = "Output/facturas_extraidas.json"
OUTPUT_FINAL = "Output/reporte_conciliacion.json"

def limpiar_nit(valor):
    """Normaliza el NIT: quita CO, puntos, guiones, espacios y ceros a la izquierda"""
    if pd.isna(valor) or valor == "":
        return "SIN_NIT"
    
    # Convertir a string y mayúsculas
    texto = str(valor).upper().strip()
    
    # Quitar sufijos
    texto = texto.replace("CO", "").replace("NIT", "").replace(".", "").replace(",", "").replace(" ", "")
    if "-" in texto:
        texto = texto.split("-")[0]
        
    return texto

def cargar_datos():
    print("Cargando datos...")
    
    # 1. Cargar Facturas extraídas JSON
    if not os.path.exists(JSON_FACTURAS):
        print("No existe el JSON de facturas. Ejecuta primero los scripts de extracción.")
        return None, None, None

    with open(JSON_FACTURAS, 'r', encoding='utf-8') as f:
        data_pdf = json.load(f)
    
    df_pdf = pd.DataFrame(data_pdf)
    
    # Separar errores
    errores_pdf = []
    if "error" in df_pdf.columns:
        errores_pdf = df_pdf[df_pdf["error"].notna()][["nombre_archivo", "error"]].to_dict(orient="records")
        df_pdf = df_pdf[df_pdf["error"].isna()] 
    
    df_pdf["nit_limpio"] = df_pdf["nit_proveedor"].apply(limpiar_nit)
    print(f"   ✅ {len(df_pdf)} facturas cargadas desde PDF.")

    # 2. Cargar Excel
    if not os.path.exists("Data"):
        print("No existe la carpeta 'Data'.")
        return None, None, None

    archivos_excel = [f for f in os.listdir("Data") if f.endswith(".xlsx")]
    if not archivos_excel:
        print("No encontré el Excel en la carpeta Data.")
        return None, None, None
    
    ruta_excel = os.path.join("Data", archivos_excel[0])
    print(f"   📄 Leyendo Excel: {ruta_excel}...")
    
    try:
        df_excel = pd.read_excel(ruta_excel, header=3)
    except Exception as e:
        print(f"Error leyendo el Excel: {e}")
        return None, None, None

    # Limpiar nombres de columnas
    df_excel.columns = df_excel.columns.str.strip()
    
    # Buscar la columna NIT 
    col_nit = next((c for c in df_excel.columns if "NIT" in str(c).upper() or "TAX" in str(c).upper()), None)
    
    if not col_nit:
        print(f"Las columnas que veo son: {list(df_excel.columns)}")
        return None, None, None

    print(f"Columna NIT detectada como: '{col_nit}'")

    # Limpieza de NIT en Excel
    df_excel["nit_limpio"] = df_excel[col_nit].apply(limpiar_nit)
    
    # Buscar columnas de montos
    col_total = next((c for c in df_excel.columns if "TOTAL" in str(c).upper() or "AMOUNT" in str(c).upper()), None)
    if col_total:
        df_excel["total_excel"] = pd.to_numeric(df_excel[col_total], errors='coerce').fillna(0)
    else:
        df_excel["total_excel"] = 0
        print("   ⚠️ Advertencia: No encontré columna de Total/Amount en Excel. Usando 0.")
    
    print(f"   ✅ {len(df_excel)} registros cargados desde Excel.")
    
    return df_pdf, df_excel, errores_pdf

def generar_grafica(conteo):
    """Genera un gráfico de pastel para el bonus"""
    etiquetas = ['Coinciden', 'Difieren', 'Solo en PDF', 'Solo en Excel']
    valores = [conteo['coinciden'], conteo['difieren'], conteo['solo_pdf'], conteo['solo_excel']]
    
    plt.figure(figsize=(8, 8))
    # Evitar error si todos son cero
    if sum(valores) == 0: valores = [1, 0, 0, 0] 

    plt.pie(valores, labels=etiquetas, autopct='%1.1f%%', colors=['#4CAF50', '#FFC107', '#2196F3', '#9E9E9E'])
    plt.title('Resultados de Conciliación de Facturas')
    
    # Crear carpeta Output si no existe
    if not os.path.exists("Output"):
        os.makedirs("Output")
        
    ruta_img = "Output/grafico_conciliacion.png"
    plt.savefig(ruta_img)
    print(f"Gráfico generado en: {ruta_img}")

def main():
    df_pdf, df_excel, errores_lectura = cargar_datos()
    
    if df_pdf is None or df_excel is None: return

    print("Cruzando información...")
    
    reporte = {
        "metadata": {
            "total_pdfs_procesados": len(df_pdf) + len(errores_lectura),
            "total_registros_excel": len(df_excel),
            "herramienta_extraccion": "Gemini Flash 1.5/2.0",
            "metodo_conciliacion": "Cruce por NIT Normalizado"
        },
        "resumen_conciliacion": {
            "coinciden": 0,
            "difieren": 0,
            "solo_pdf": 0,
            "solo_excel": 0
        },
        "proveedores": [],
        "errores_y_excepciones": errores_lectura
    }

    # Cruce
    cruce = pd.merge(df_pdf, df_excel, on="nit_limpio", how="outer", indicator=True, suffixes=('_pdf', '_excel'))
    
    for _, row in cruce.iterrows():
        estado = ""
        detalles = {}
        nit_actual = row["nit_limpio"]
        
        # Coinciden
        if row["_merge"] == "both":
            monto_pdf = float(row.get("total", 0))
            monto_excel = float(row.get("total_excel", 0))
            diferencia = abs(monto_pdf - monto_excel)
            
            if diferencia < 1000: # Tolerancia de $1,000 pesos
                estado = "Coinciden"
                reporte["resumen_conciliacion"]["coinciden"] += 1
            else:
                estado = "Difieren"
                reporte["resumen_conciliacion"]["difieren"] += 1
                detalles["diferencia_monto"] = {
                    "valor_pdf": monto_pdf,
                    "valor_excel": monto_excel,
                    "delta": diferencia
                }
            
            reporte["proveedores"].append({
                "nit": nit_actual,
                "nombre": row.get("nombre_proveedor", "N/A"),
                "estado": estado,
                "hallazgos": detalles
            })
            
        # Solo PDF
        elif row["_merge"] == "left_only":
            reporte["resumen_conciliacion"]["solo_pdf"] += 1
            reporte["proveedores"].append({
                "nit": nit_actual,
                "nombre": row.get("nombre_proveedor", "N/A"),
                "estado": "No encontrado en Excel",
                "hallazgos": "Factura existe físicamente pero no en el listado contable."
            })
            
        # Solo Excel
        elif row["_merge"] == "right_only":
            reporte["resumen_conciliacion"]["solo_excel"] += 1

    # Guardar JSON Final
    with open(OUTPUT_FINAL, 'w', encoding='utf-8') as f:
        json.dump(reporte, f, indent=4, ensure_ascii=False)
    
    print(f"\nREPORTE FINAL GENERADO: {OUTPUT_FINAL}")
    
    # Generar Bonus
    generar_grafica(reporte["resumen_conciliacion"])

if __name__ == "__main__":
    main()