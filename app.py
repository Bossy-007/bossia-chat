import os
import requests
from flask import Flask, render_template, request, jsonify
from groq import Groq
from supabase import create_client, Client

app = Flask(__name__)

# Configuración de Groq
groq_key = os.environ.get(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)
tavily_key = os.environ.get(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)
client = Groq(api_key=groq_key)

# Configuración de Supabase
supabase_url = os.environ.get(https://evhexbbblhzvuxnqxnuy.supabase.co/rest/v1/)
supabase_key = os.environ.get(sb_publishable_bj_iRjREHu6xoNBgxp-GQw_uoJo4IZl)
supabase: Client = create_client(supabase_url, supabase_key) if supabase_url and supabase_key else None

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

# --- RUTAS DE GESTIÓN DE CHATS ---

@app.route("/api/chats", methods=["GET"])
def get_chats():
    """Obtiene la lista de conversaciones guardadas"""
    if not supabase:
        return jsonify([])
    res = supabase.table("chats").select("*").order("created_at", desc=True).execute()
    return jsonify(res.data)

@app.route("/api/chats", methods=["POST"])
def create_chat():
    """Crea una nueva conversación"""
    if not supabase:
        return jsonify({"error": "No DB"}), 500
    res = supabase.table("chats").insert({"title": "Nuevo Chat"}).execute()
    return jsonify(res.data[0])

@app.route("/api/chats/<chat_id>/messages", methods=["GET"])
def get_messages(chat_id):
    """Obtiene los mensajes de un chat específico"""
    if not supabase:
        return jsonify([])
    res = supabase.table("messages").select("*").eq("chat_id", chat_id).order("created_at", desc=False).execute()
    return jsonify(res.data)

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message", "")
    chat_id = data.get("chat_id")

    if not user_message or not chat_id:
        return jsonify({"error": "Faltan datos"}), 400

    # Guardar mensaje del usuario en la BD
    if supabase:
        supabase.table("messages").insert({"chat_id": chat_id, "role": "user", "content": user_message}).execute()

    # Cargar historial del chat para dar contexto a Groq
    history = []
    if supabase:
        msg_history = supabase.table("messages").select("role, content").eq("chat_id", chat_id).order("created_at", desc=False).execute()
        history = [{"role": m["role"], "content": m["content"]} for m in msg_history.data[:-1]]

    info_web = buscar_en_web(user_message)
    system_prompt = (
        "Eres BossIA, un asistente inteligente, directo y conciso.\n"
        "REGLAS:\n"
        "- Sé breve, claro y ve directo al grano.\n"
        "- Si el usuario solo saluda, responde en 1 o 2 frases corto y amigable.\n"
        "- Utiliza información de Internet solo si es relevante:\n"
        f"{info_web}"
    )

    messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": user_message}]

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.5,
            max_tokens=500,
        )
        bot_response = completion.choices[0].message.content

        # Guardar respuesta del bot en la BD
        if supabase:
            supabase.table("messages").insert({"chat_id": chat_id, "role": "assistant", "content": bot_response}).execute()
            # Actualizar el título del chat con el primer mensaje del usuario
            supabase.table("chats").update({"title": user_message[:30] + "..."}).eq("id", chat_id).execute()

        return jsonify({"response": bot_response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
