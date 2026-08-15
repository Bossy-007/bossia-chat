import os
import uuid
import requests
from flask import Flask, render_template, request, jsonify
from groq import Groq
from supabase import create_client, Client
from functools import wraps

app = Flask(__name__)

# Configuración de Claves
groq_key = os.environ.get("GROQ_API_KEY")
tavily_key = os.environ.get("TAVILY_API_KEY")
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")

client = Groq(api_key=groq_key) if groq_key else None

supabase: Client = None
if supabase_url and supabase_key:
    try:
        # Limpiamos la URL por si tiene sufijos
        clean_url = supabase_url.split("/rest/v1")[0]
        supabase = create_client(clean_url, supabase_key)
    except Exception as e:
        print(f"Error al conectar con Supabase: {e}")

# Memoria local de respaldo por si Supabase falla
local_chats = {}

def get_user_from_token(req):
    auth_header = req.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ")[1]
    try:
        user_response = supabase.auth.get_user(token)
        return user_response.user.id
    except Exception as e:
        print(f"Error validando token: {e}")
        return None
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
    return render_template(
        "index.html",
        supabase_url=os.environ.get("SUPABASE_URL"),
        supabase_anon_key=os.environ.get("SUPABASE_ANON_KEY")  # nueva variable, la publishable
    )

@app.route("/api/chats", methods=["GET"])
def get_chats():
    user_id = get_user_from_token(request)
    if not user_id:
        return jsonify({"error": "No autorizado"}), 401
    if supabase:
        try:
            res = supabase.table("chats").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
            return jsonify(res.data)
        except Exception as e:
            print(f"Error obteniendo chats de Supabase: {e}")
    return jsonify([])

@app.route("/api/chats", methods=["POST"])
def create_chat():
    user_id = get_user_from_token(request)
    if not user_id:
        return jsonify({"error": "No autorizado"}), 401
    if supabase:
        try:
            res = supabase.table("chats").insert({"title": "Nuevo Chat", "user_id": user_id}).execute()
            if res.data:
                return jsonify(res.data[0])
        except Exception as e:
            print(f"Error creando chat en Supabase: {e}")
            return jsonify({"error": "No se pudo crear el chat"}), 500
    
    # Fallback local
    new_id = str(uuid.uuid4())
    local_chats[new_id] = {"title": "Nuevo Chat", "messages": []}
    return jsonify({"id": new_id, "title": "Nuevo Chat"})

@app.route("/api/chats/<chat_id>", methods=["DELETE"])
def delete_chat(chat_id):
    if supabase:
        try:
            supabase.table("chats").delete().eq("id", chat_id).execute()
            return jsonify({"success": True})
        except Exception as e:
            print(f"Error borrando chat: {e}")
            return jsonify({"error": str(e)}), 500

    # Fallback local
    if chat_id in local_chats:
        del local_chats[chat_id]
    return jsonify({"success": True})
@app.route("/api/chats/<chat_id>/messages", methods=["GET"])
def get_messages(chat_id):
    if supabase:
        try:
            res = supabase.table("messages").select("*").eq("chat_id", chat_id).order("created_at", desc=False).execute()
            return jsonify(res.data)
        except Exception as e:
            print(f"Error obteniendo mensajes de Supabase: {e}")
    
    # Fallback local
    chat = local_chats.get(chat_id, {})
    return jsonify(chat.get("messages", []))

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json or {}
    user_message = data.get("message", "")
    chat_id = data.get("chat_id")

    if not user_message:
        return jsonify({"error": "Mensaje vacío"}), 400

    # Guardar mensaje del usuario
    if supabase and chat_id:
        try:
            supabase.table("messages").insert({"chat_id": chat_id, "role": "user", "content": user_message}).execute()
        except Exception as e:
            print(f"Error guardando mensaje usuario: {e}")
    elif chat_id and chat_id in local_chats:
        local_chats[chat_id]["messages"].append({"role": "user", "content": user_message})

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

        # Guardar respuesta del bot y actualizar título
        if supabase and chat_id:
            try:
                supabase.table("messages").insert({"chat_id": chat_id, "role": "assistant", "content": bot_response}).execute()
                title_summary = user_message[:25] + ("..." if len(user_message) > 25 else "")
                supabase.table("chats").update({"title": title_summary}).eq("id", chat_id).execute()
            except Exception as e:
                print(f"Error guardando respuesta bot: {e}")
        elif chat_id and chat_id in local_chats:
            local_chats[chat_id]["messages"].append({"role": "assistant", "content": bot_response})
            local_chats[chat_id]["title"] = user_message[:25]

        return jsonify({"response": bot_response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
