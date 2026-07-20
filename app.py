import os
import urllib.parse
import urllib.request
import re
from flask import Flask, render_template, request, jsonify
from groq import Groq

app = Flask(__name__)

api_key = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=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)

def buscar_en_web(query):
    """Busca información actualizada en la web usando DuckDuckGo Lite"""
    try:
        url = "https://lite.duckduckgo.com/lite/"
        data = urllib.parse.urlencode({'q': query}).encode('utf-8')
        req = urllib.request.Request(
            url, 
            data=data,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            html = response.read().decode('utf-8', errors='ignore')
            # Limpiamos las etiquetas HTML para quedarnos solo con el texto útil
            texto_limpio = re.sub(r'<[^>]+>', ' ', html)
            lineas = [linea.strip() for linea in texto_limpio.split('\n') if len(linea.strip()) > 30]
            # Cogemos las primeras líneas con información relevante
            resultado = " ".join(lineas[:6])
            return resultado[:1500] # Limitamos la cantidad de texto
    except Exception as e:
        return ""

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message", "")
    history = data.get("history", [])

    if not user_message:
        return jsonify({"error": "Mensaje vacío"}), 400

    # 1. Obtenemos datos de la red
    info_web = buscar_en_web(user_message)

    # 2. Le damos las instrucciones explícitas al modelo
    system_prompt = (
        "Eres BossIA, un asistente virtual actualizado e inteligente. "
        "Tienes acceso a información extraída en tiempo real de Internet. "
        "Usa los siguientes datos de la web para responder con precisión y actualidad al usuario:\n\n"
        f"--- DATOS DE INTERNET ---\n{info_web}\n-------------------------\n\n"
        "Si los datos contienen la respuesta, utilízalos directamente. No digas que no puedes acceder a Internet."
    )

    messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": user_message}]

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.5,
            max_tokens=1024,
        )
        bot_response = completion.choices[0].message.content
        return jsonify({"response": bot_response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
