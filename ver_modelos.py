import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

print("Consultando modelos...")

try:
    # Listar todos los modelos disponibles
    for m in genai.list_models():
        # Solo mostrar los que sirven
        if 'generateContent' in m.supported_generation_methods:
            print(f"Disponible: {m.name}")
            
except Exception as e:
    print(f"Error grave: {e}")
