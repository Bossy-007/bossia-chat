import os
import requests
from flask import Flask, render_template, request, jsonify
from groq import Groq

app = Flask(__name__)

# Carga las claves desde las Variables de Entorno de Render
groq_key = os.environ.get("GROQ_API_KEY")
tavily_key = os.environ.get("TAVILY_API_KEY")

# Conecta con Groq usando la variable groq_key
client = Groq(api_key=groq_key)

def buscar_en_web(consulta):
    if not tavily_key:
        return ""
    try:
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": tavily_key,
                "query": consulta,
                "search_depth": "basic",
                "max_results": 3
            },
            timeout=5
        )
        data = response.json()
        resultados = data.get("results", [])
        
        texto = ""
        for item in resultados:
            texto += f"- {item.get('title')}: {item.get('content')}\n"
        return texto
    except Exception:
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

    info_web = buscar_en_web(user_message)

    system_prompt = (
        "Eres BossIA, un asistente inteligente, directo y conciso.\n"
        "REGLAS DE RESPUESTA:\n"
        "- Sé breve, claro y ve directo al grano. Evita párrafos largos innecesarios.\n"
        "- Si el usuario solo saluda (ej. 'hola'), responde de forma amigable y corta en 1 o 2 frases máximo.\n"
        "- Responde utilizando formato limpio (puntos, negritas) cuando sea útil para facilitar la lectura.\n"
        "- Utiliza la siguiente información de Internet solo si el usuario hizo una pregunta actual o de búsqueda:\n"
        f"{info_web}"
    )

    messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": user_message}]

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
        )
        bot_response = completion.choices[0].message.content
        return jsonify({"response": bot_response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
