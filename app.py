import os
import requests
from flask import Flask, render_template, request, jsonify
from groq import Groq
from supabase import create_client, Client

app = Flask(__name__)

# Configuración de Groq
groq_key = os.environ.get("GROQ_API_KEY")
tavily_key = os.environ.get("TAVILY_API_KEY")
client = Groq(api_key=groq_key)

# Configuración de Supabase
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")

supabase: Client = None
if supabase_url and supabase_key:
    try:
        supabase = create_client(supabase_url, supabase_key)
    except Exception as e:
        print(f"Error conectando a Supabase: {e}")

def buscar_en_web(consulta):
    if not tavily_key:
        return ""
    try:
        response = requests.post(
            "https://api.tavily.com/search",
            json={"api_key": tavily_key, "query": consulta, "search_depth": "basic", "max_results": 3},
            timeout=5
        )
        resultados = response.json().get("results", [])
        return "".join([f"- {item.get('title')}: {item.get('content')}\n" for item in resultados])
    except Exception:
        return ""

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/chats", methods=["GET"])
def get_chats():
    if not supabase:
        return jsonify([])
    try:
        res = supabase.table("chats").select("*").order("created_at", desc=True).execute()
        return jsonify(res.data)
    except Exception:
        return jsonify([])

@app.route("/api/chats", methods=["POST"])
def create_chat():
    if not supabase:
        return jsonify({"id": "default"})
    try:
        res = supabase.table("chats").insert({"title": "Nuevo Chat"}).execute()
        return jsonify(res.data[0])
    except Exception:
        return jsonify({"id": "default"})

@app.route("/api/chats/<chat_id>/messages", methods=["GET"])
def get_messages(chat_id):
    if not supabase or chat_id == "default":
        return jsonify([])
    try:
        res = supabase.table("messages").select("*").eq("chat_id", chat_id).order("created_at", desc=False).execute()
        return jsonify(res.data)
    except Exception:
        return jsonify([])

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message", "")
    chat_id = data.get("chat_id")

    if not user_message:
        return jsonify({"error": "Mensaje vacío"}), 400

    # Guardar en BD si está disponible
    if supabase and chat_id and chat_id != "default":
        try:
            supabase.table("messages").insert({"chat_id": chat_id, "role": "user", "content": user_message}).execute()
        except Exception as e:
            print(f"Error guardando mensaje usuario: {e}")

    info_web = buscar_en_web(user_message)
    system_prompt = (
        "Eres BossIA, un asistente inteligente, directo y conciso.\n"
        "REGLAS:\n"
        "- Sé breve, claro y ve directo al grano.\n"
        "- Si el usuario solo saluda, responde amigablemente en 1 o 2 frases.\n"
        "- Usa esta info web solo si la pregunta requiere datos actuales:\n"
        f"{info_web}"
    )

    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}]

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.5,
            max_tokens=500,
        )
        bot_response = completion.choices[0].message.content

        if supabase and chat_id and chat_id != "default":
            try:
                supabase.table("messages").insert({"chat_id": chat_id, "role": "assistant", "content": bot_response}).execute()
                supabase.table("chats").update({"title": user_message[:25] + "..."}).eq("id", chat_id).execute()
            except Exception as e:
                print(f"Error guardando respuesta bot: {e}")

        return jsonify({"response": bot_response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
