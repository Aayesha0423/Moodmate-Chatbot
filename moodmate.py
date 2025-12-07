
# MoodMate: Your AI Companion Chatbot
# Compatible with Gradio 4.x / 5.x

import os
import json
import requests
import gradio as gr
from packaging import version

# ---------------- GROQ API SETUP ----------------
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY not found. Run: os.environ['GROQ_API_KEY']='your_key' in this notebook.")

GROQ_BASE = "https://api.groq.com/openai/v1"

def call_groq_api(messages):
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": messages,
        "temperature": 0.9,
        "max_tokens": 512
    }
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    url = f"{GROQ_BASE}/chat/completions"
    resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)

    if resp.status_code == 401:
        raise RuntimeError("401 Unauthorized — invalid or revoked GROQ_API_KEY.")
    if resp.status_code != 200:
        raise RuntimeError(f"Groq API error {resp.status_code}: {resp.text[:400]}")

    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        raise RuntimeError("Unexpected Groq response shape: " + json.dumps(data)[:800])

# ---------------- CORE CHATBOT LOGIC ----------------
def mood_chatbot(user_input, history=None):
    if history is None:
        history = []

    q = user_input.lower()
    if "who made you" in q or "creator" in q or "owner" in q:
        reply = "I was created by Shrusha ✨"
        history.append((user_input, reply))
        return reply, history

    if len(history) == 0:
        starter = "Hey 👋 How’s everything going today? Tell me how you feel."
        history.append(("", starter))
        return starter, history

    system_msg = {
        "role":"system",
        "content": "You are a friendly AI companion. Ask about mood and respond kindly. Comfort if sad, celebrate if happy."
    }

    messages = [system_msg]
    for u, a in history:
        messages.append({"role":"user", "content": str(u)})
        messages.append({"role":"assistant", "content": str(a)})
    messages.append({"role":"user", "content": str(user_input)})

    assistant_text = call_groq_api(messages)
    history.append((str(user_input), assistant_text))
    return assistant_text, history

# ---------------- GRADIO COMPATIBILITY ----------------
def safe_respond(user_message, history):
    if history is None:
        history = []

    try:
        reply_text, new_history = mood_chatbot(user_message, history)
    except Exception as e:
        err = f"[Error] {e}"
        new_history = history[:]
        new_history.append((str(user_message), err))

    gr_ver = getattr(gr, "__version__", "0.0.0")
    is_v4 = version.parse(gr_ver) < version.parse("5.0.0")

    if is_v4:
        chatbot_value = [(str(u), str(a)) for u, a in new_history]
    else:
        chatbot_value = []
        for u, a in new_history:
            chatbot_value.append({"role":"user","content":str(u)})
            chatbot_value.append({"role":"assistant","content":str(a)})

    safe_state = [(str(u), str(a)) for u, a in new_history]
    return chatbot_value, safe_state

# ---------------- GRADIO UI ----------------
css = """
#chatbot { background: linear-gradient(135deg,#ff9a9e 0%,#fad0c4 100%); border-radius:20px; padding:15px; font-family:'Segoe UI',sans-serif;}
#chatbot .wrap { border-radius:12px; padding:8px; font-size:16px; }
textarea { border-radius:10px !important; border:2px solid #ff758c !important; }
button { border-radius:12px !important; background:#ff758c !important; color:white !important; font-weight:bold; }
"""

with gr.Blocks() as demo:
    gr.HTML(f"<style>{css}</style>")
    chatbot_ui = gr.Chatbot(label="🌸 MoodMate: Your AI Companion", elem_id="chatbot")
    msg = gr.Textbox(placeholder="Type how you feel...", label="Your Message")
    clear = gr.Button("Clear Chat")
    state = gr.State([])

    msg.submit(safe_respond, [msg, state], [chatbot_ui, state]).then(lambda: "", None, msg)
    clear.click(lambda: [], None, [chatbot_ui, state])

demo.launch(inbrowser=True, share=False)