import os
import requests
from flask import Flask, render_template, request, jsonify
from groq import Groq

app = Flask(__name__)

groq_key = os.environ.get(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)
tavily_key = os.environ.get(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)

client = Groq(api_key=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)

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
        "Eres BossIA, un asistente inteligente y actualizado. "
        "Utiliza la siguiente información reciente extraída de Internet para responder con datos actuales:\n"
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
