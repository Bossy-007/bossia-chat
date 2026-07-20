import os
from flask import Flask, render_template, request, jsonify
from groq import Groq
from duckduckgo_search import DDGS

app = Flask(__name__)

api_key = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=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)

def buscar_en_web(query):
    """Busca en Internet los últimos resultados de DuckDuckGo"""
    try:
        results = DDGS().text(query, max_results=3)
        texto_resultados = ""
        for r in results:
            texto_resultados += f"- {r['title']}: {r['body']}\n"
        return texto_resultados
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

    # 1. Buscamos información fresca en Internet
    info_web = buscar_en_web(user_message)

    # 2. Creamos la instrucción con los datos encontrados
    system_prompt = (
        "Eres BossIA, un asistente útil y moderno. "
        "Usa la siguiente información reciente de Internet si es relevante para responder a la pregunta del usuario:\n"
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
