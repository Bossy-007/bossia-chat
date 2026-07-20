import os
import json
import urllib.parse
import urllib.request
from flask import Flask, render_template, request, jsonify
from groq import Groq

app = Flask(__name__)

api_key = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=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)

def buscar_en_web(query):
    """Busca en Internet usando la API HTML ligera de DuckDuckGo"""
    try:
        url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=4) as response:
            html = response.read().decode('utf-8')
            # Extraemos texto simple
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            snippets = [a.get_text() for a in soup.find_all('a', class_='result__snippet')][:3]
            return "\n".join(snippets)
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
        "Eres BossIA, un asistente moderno y directo. "
        "Si la siguiente información web es útil para la duda del usuario, úsala:\n"
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
