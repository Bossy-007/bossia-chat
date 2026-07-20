import os
from flask import Flask, render_template, request, jsonify
from groq import Groq

app = Flask(__name__)

api_key = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=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)

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

    messages = [{"role": "system", "content": "Eres BossIA, un asistente útil y directo."}] + history + [{"role": "user", "content": user_message}]

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
