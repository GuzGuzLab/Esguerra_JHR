# Pipeline de Extracción y Conciliación de Facturas (AI)

Este proyecto automatiza el proceso de auditoría contable entre facturas en formato PDF y un listado maestro en Excel (AP Listing) Utiliza Inteligencia Artificial Generativa para la extracción de datos no estructurados

##  Características
- **Extracción Inteligente:** Uso de Google Gemini 1.5 Flash para interpretar diferentes diseños de facturas
- **Procesamiento Robusto:** Manejo de límites de cuota (Rate Limiting) con lógica de reintentos
- **Análisis de Datos:** Cruce de información con Pandas, normalización de NITs y cálculo de discrepancias
- **Visualización:** Generación automática de reportes en JSON y gráficos estadísticos

## Tecnologías
- **Python 3.12**
- **Pandas** (Procesamiento de datos)
- **Google Generative AI** (LLM para extracción)
- **Matplotlib** (Visualización)

## Instalación y Configuración

 **Clonar el repositorio:**
   ```bash
   git clone [https://github.com/GuzGuzLab/Esguerra_JHR.git](https://github.com/GuzGuzLab/Esguerra_JHR.git)