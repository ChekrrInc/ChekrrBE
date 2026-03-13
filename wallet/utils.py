from django.conf import settings
from groq import Groq
import requests
from .models import Wallet

start_prompt = "You are an ai bot named Chekrr that help people turn their product description into a global payment link,keep response under 300 words"

class ChekrrBot:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.sessions = {}  # phone → chat session
        self.onboarding_status={}
        self.onboarding_info={}
        self.sent_greeting_text=False


    def setupMasterWallet(self):
        print("Setting up master")
        if wallet.objects.filter(title="Master Wallet").exists():
            print("Master wallet already created")
            



    def get_history(self, phone: str):
        if phone not in self.sessions:
            self.sessions[phone] = [
                {"role": "system", "content": start_prompt}
            ]

        if phone not in self.onboarding_status:
            self.onboarding_status[phone]=True
            return self.sessions[phone]
        return self.sessions[phone]
 
    def reply(self, phone: str, message: str) -> str:
        history = self.get_history(phone)

        # add user message to history
        history.append({"role": "user", "content": message})

        obj=Wallet.objects.filter(number_id=phone)
        if obj.exists():
            obj = obj[0]
            history.append({
                "role": "system",
                "content": (
                    "The user's last message is below. Identify if they are asking about their account details. "
                    "Reply with ONLY one of these exact keywords based on what they are asking for:\n"
                    "'merchant_name' - if asking about their name or merchant name\n"
                    "'store_name'    - if asking about their store or brand name\n"
                    "'wallet_address'- if asking about their wallet, stacks wallet, or STX address\n"
                    "'phone'         - if asking about their phone number or number ID\n"
                    "'all'           - if asking for all their details or full profile\n"
                    "'false'         - if not asking about account details at all\n\n"
                    "Reply with the keyword ONLY — no other text.\n\n"
                   f"User message: {message}"
                )
            })

            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=self.get_history(phone)
            )

            result = response.choices[0].message.content.strip().lower()
            responses = {
                "merchant_name":  f"👤 Your merchant name is *{obj.title}*",
                "store_name":     f"🏪 Your store brand name is *{obj.store_name}*",
                "wallet_address": f"💳 Your Stacks wallet address is:\n`{obj.wallet_address}`",
                "phone":          f"📞 Your phone number is *{obj.number_id}*",
                "all": (
                    f"*Your Merchant Profile* 👤\n\n"
                    f"👤 Merchant Name: *{obj.title}*\n"
                    f"🏪 Store Brand: *{obj.store_name}*\n"
                    f"📞 Phone: *{obj.number_id}*\n\n"
                    f"💳 Stacks Wallet Address:\n\n{obj.wallet_address}"
                )
            }

            if result in responses:
                 return responses[result]
            return "Logged in terminal" 
              

        reply = response.choices[0].message.content



        resp=(
              "👋 Hi! Welcome to *Chekrr* 🛍️\n\n"
              "I help merchants like you turn product descriptions into global payment links in seconds.\n\n"
              "Reply *start* to set up your store and begin accepting payments worldwide 🌍 powered by Stacks"
                )

        if self.onboarding_status[phone]:
              history.append({"role": "assistant", "content": resp})
              if self.onboarding_status[phone] != "pending":
                 self.onboarding_status[phone]="pending"
                 self.sent_greeting_text=True
                 return resp

              if phone not in self.onboarding_info and "start" in message.strip().lower():
                 return (
       "Please reply with:\n"
        "👤 *Your name*\n"
        "🏪 *Your store brand name*\n"
        "\n"
        "To finish onboarding and link you with your stacks onchain wallet\n"
        "Reply order [your name],[your store brand name]"

    )
              if "," in message:
                if Wallet.objects.filter(number_id=phone).exists():
                   return "Merchant Profile Already exists for this mobile number"

                data=message.split(",")
                res_data=requests.get("http://localhost:8080/wallet/create")
                obj=Wallet.objects.create(
                    title=f"{data[0]}",
                    store_name=data[1],
                    merchant_name=data[0],
                    password=res_data.json()["password"],
                    secret_key=res_data.json()["secretKey"],
                    wallet_address=res_data.json()["address"],
                    number_id=phone
                )
                self.onboarding_info[phone]="done"
                self.onboarding_status[phone]="done"

                return (f"*Merchant Profile Created*\n\nMerchant Name:{data[0]}\nStore Brand Name:{data[1]}\n\nStacks Wallet Address:\n{res_data.json()['address']}")
             
              if self.sent_greeting_text:
                    return ( "Reply with *start* to finish onboarding. \n"
                    "Reply order [your name],[your store brand name]"

)

        response = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=history
        )

        reply = response.choices[0].message.content

        # add assistant reply to history
        history.append({"role": "system", "content": reply})

        return reply

def parse_whatsapp_dict(payload: dict) -> dict:
    value    = payload["entry"][0]["changes"][0]["value"]
    if "contacts" not in value:
        return None

    contact  = value["contacts"][0]
    message  = value["messages"][0]

    return {
        "name":    contact["profile"]["name"],
        "phone":   contact["wa_id"],
        "message": message["text"]["body"],
        "type":    message["type"],
    }

def reply_whatsapp_message(msg:str,to:str): 
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


def handle_chat_reply(msg:str)->str:
    return 


