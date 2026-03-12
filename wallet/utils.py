from django.conf import settings
from groq import Groq
import requests

start_prompt = "You are an ai bot named Chekrr that help people turn their product description into a global payment link,keep response under 300 words"

class ChekrrBot:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.sessions = {}  # phone → chat session
    
    def get_history(self, phone: str):
        if phone not in self.sessions:
            self.sessions[phone] = [
                {"role": "system", "content": start_prompt}
            ]
        return self.sessions[phone]
 
    def reply(self, phone: str, message: str) -> str:
        history = self.get_history(phone)

        # add user message to history
        history.append({"role": "user", "content": message})

        response = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=history
        )

        reply = response.choices[0].message.content

        # add assistant reply to history
        history.append({"role": "assistant", "content": reply})

        return reply

def parse_whatsapp_dict(payload: dict) -> dict:
    value    = payload["entry"][0]["changes"][0]["value"]
    contact  = value["contacts"][0]
    message  = value["messages"][0]

    return {
        "name":    contact["profile"]["name"],
        "phone":   contact["wa_id"],
        "message": message["text"]["body"],
        "type":    message["type"],
    }

def reply_whatsapp_message(msg:str,to:str):
    print(msg,to)
    headers = {
       "Authorization": f"Bearer {settings.WHATSAPP_BUSINESS_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {
            "body": f"{msg}",
                    }
    }

    response = requests.post(settings.FACEBOOK_GRAPH_API, headers=headers, json=payload)
    return response.json()

