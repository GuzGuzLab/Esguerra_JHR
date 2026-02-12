import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("ERROR: No encontré la API Key.")
else:
    print(f"Llave cargada: {api_key[:5]}...")

    try:
        genai.configure(api_key=api_key)
        
        model = genai.GenerativeModel('models/gemini-flash-latest') 

        print("Probando conexión con Gemini Flash Latest...")
        response = model.generate_content("Responde solo con la palabra: ¡CONECTADO!")
        
        print(f"\nRespuesta de Gemini: {response.text}")
        print("Conexión exitosa.")
        
    except Exception as e:
        print(f"\nError: {e}")