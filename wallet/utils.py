from django.conf import settings
from groq import Groq
import requests
import re
import base64
import hashlib
from .models import Wallet
from product.models import Product

start_prompt = "You are an ai bot named Chekrr that help people turn their product description into a global payment link,keep response under 300 words"


import json

client = Groq(api_key=settings.GROQ_API_KEY)

def extract_product_details_ai(message: str) -> dict:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{
            "role": "system",
            "content": (
                "Extract product details from the user's message and return ONLY a valid JSON object "
                "with exactly these fields:\n"
                "- title: product name (string)\n"
                "- description: what the product is (string)\n"
                "- price: numeric value only, no currency symbols (float)\n"
                "- quantity: numeric value only (int)\n\n"
                "If a field is not mentioned, set it to null.\n"
                "Return ONLY the JSON object — no explanation, no markdown, no backticks."
            )
        }, {
            "role": "user",
            "content": message
        }],
        temperature=0,
    )

    raw = response.choices[0].message.content.strip()

    try:
        data = json.loads(raw)
        return {
            "title": data.get("title"),
            "description": data.get("description"),
            "price": float(data["price"]) if data.get("price") else None,
            "quantity": int(data["quantity"]) if data.get("quantity") else None,
        }

    except json.JSONDecodeError:
        return {
            "title": None,
            "description": None,
            "price": None,
            "quantity": None,
        }

def extract_transfer_details(text: str) -> dict:
    # Match amount (int or float) followed by usdcx (case insensitive)
    amount_match = re.search(r'(\d+(?:\.\d+)?)\s*usdcx', text, re.IGNORECASE)
    
    # Match Stacks address (starts with SP or ST, 30-41 chars)
    address_match = re.search(r'\b(S[PT][A-Z0-9]{28,39})\b', text)

    amount = float(amount_match.group(1)) if amount_match else None
    address = address_match.group(1) if address_match else None

    return {
        "amount": amount,
        "address": address,
        "valid": amount is not None and address is not None
    }


def extract_product_details(text: str) -> dict:
    result = {}
    fields = ["title", "description", "price", "quantity"]
    
    for field in fields:
        match = re.search(rf'{field}\s*:\s*([^,]+)', text, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            # clean $ from price and convert to float
            if field == "price":
                value = float(re.sub(r'[^\d.]', '', value))
            # convert quantity to int
            elif field == "quantity":
                value = int(value)
            result[field] = value
        else:
            result[field] = None

    return result

class WhatsappMultiMediaMessageHandler:
    def __init__(self,whatsapp_message_packet):
        self.whatsapp_message_packet=whatsapp_message_packet
        
    def parse(self):
        value = self.whatsapp_message_packet["entry"][0]["changes"][0]["value"]

        if "contacts" not in value:
            return

        contact = value["contacts"][0]
        message = value["messages"][0]


        if message["type"] == "image":
              image_id = message["image"]["id"]
              caption = message["image"].get("caption", "")
              image_url=self._get_media_url(image_id)
              imageBytes=self._download_media(image_url)
              return { 
                "imageBase64Format":base64.b64encode(imageBytes).decode("utf-8"),
                "message": f"{caption} - has image", 
                "name":    contact["profile"]["name"],
                "phone":   contact["wa_id"],
                "type":    message["type"],
                "id":      message["id"]
             }

        if message["type"] == "text":
            return {
                "name":    contact["profile"]["name"],
                "phone":   contact["wa_id"],
                "message": message["text"]["body"],
                "type":    message["type"],
                "id":      message["id"]
            }


    def _get_media_url(self,media_id: str) -> str:
        response = requests.get(
              f"https://graph.facebook.com/v18.0/{media_id}",
        headers={"Authorization": f"Bearer {settings.WHATSAPP_BUSINESS_ACCESS_TOKEN}"}
    )
        return response.json()["url"]
    
    def _download_media(self,media_url: str) -> bytes:
        response = requests.get(
            media_url,
            headers={"Authorization": f"Bearer {settings.WHATSAPP_BUSINESS_ACCESS_TOKEN}"}
    )
        return response.content  # raw image bytes

   

class ChekrrBot:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.sessions = {}  # phone → chat session
        self.onboarding_status={}
        self.onboarding_info={}
        self.checkout_content_confirmed={}
        self.sent_greeting_text=False
        self.setupMasterWallet()


    def setupMasterWallet(self):
        print("Setting up master")
        
        obj=Wallet.objects.filter(title="Master Wallet")
        if obj.exists():
            print("Master wallet already created")
            print(f"MASTER WALLET ADDRESS:{obj[0].wallet_address}")
            return

        res_data=requests.get("http://localhost:8080/wallet/create")
        obj=Wallet.objects.create(
            title=f"Master Wallet",
            password=res_data.json()["password"],
            secret_key=res_data.json()["secretKey"],
            wallet_address=res_data.json()["address"],
            stx_private_key=res_data.json()["stxPrivateKey"]
        )

        print(f"MASTER WALLET ADDRESS:f{obj.wallet_address}")
        print("Master wallet setup successfully")



    def get_history(self, phone: str):
        if phone not in self.sessions:
            self.sessions[phone] = [
                {"role": "system", "content": start_prompt}
            ]

        if phone not in self.onboarding_status:
            self.onboarding_status[phone]=True
            return self.sessions[phone]
        return self.sessions[phone]
 
    def reply(self, phone: str, message: str,id:str,img_url:str) -> str:
        headers = {
             "Authorization": f"Bearer {settings.WHATSAPP_BUSINESS_ACCESS_TOKEN}",
             "Content-Type": "application/json"
        }

        payload = {
             "messaging_product": "whatsapp",
            "status": "read",
            "message_id": f"{id}",
            "typing_indicator": {
                "type": "text"
            }
        }

        response = requests.post(settings.FACEBOOK_GRAPH_API, headers=headers, json=payload)
  

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
                    "'all'           - if asking for profile"
                    "'balance'       - if is asking about wallet balance or wallet holding or usdcx amount balance"
                    "'send'          - if is asking about to transfer usdcx or send usdcx or move usdcx"
                    "'payment_link'  - if is giving description of a product or 'has image'"
                    "'false'         - if not asking about account details at all\n\n"
                    "Reply with the keyword ONLY — no other text.\n\n"
                   f"User message: {message}"
                )
            })

            response_ = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=self.get_history(phone)
            )

            result = response_.choices[0].message.content.strip().lower()
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

            if result == "balance":
                res_data=requests.post("http://localhost:8080/wallet/status",json={ "walletAddress": obj.wallet_address })
                print(res_data.json())
                if "error" in res_data.json():
                    return "Your wallet balance is 0 USDCx"
                return f"Your wallet balance is {res_data.json()['walletBalance']} USDCx"
            
            if result == "send":
                masterWallet=Wallet.objects.filter(title="Master Wallet")
                userWallet=Wallet.objects.filter(number_id=phone)
                if masterWallet[0]:
                    userSendData=extract_transfer_details(message)
                    res_data=requests.post("http://localhost:8080/wallet/send",json={
                        "usdcxAmount":userSendData["amount"],
                        "recvAddress":userSendData["address"],
                        "senderAddress":userWallet[0].wallet_address,
                        "senderPrivateKey":userWallet[0].stx_private_key,
                        "sponsorPrivateKey":masterWallet[0].stx_private_key
                    })
                    return f"Sent {userSendData['amount']} to {userSendData['address']}\n\nTransaction Hash:\nhttps://explorer.hiro.so/txid/{res_data.json()['txid']}?chain=testnet"
                return f"An Issue Occurred don't worry it is not you it is us"

            if result == "payment_link":
                if "- has image" not in message:
                    return "Product image missing"
                product_prompt = [{
    "role": "system",
    "content": (
        "The user is trying to create a product. Extract the following required fields from their message:\n"
        "- title (the product name)\n"
        "- description (what the product is)\n"
        "- price (how much it costs)\n"
        "- quantity (how many are available)\n\n"
        "If ALL fields are present, reply with ONLY: 'complete'\n"
        "If ANY fields are missing, reply with ONLY this format: '<field1>, <field2> field(s) are missing'\n"
        "Examples:\n"
        "  Missing title only → 'Title field is missing'\n"
        "  Missing price and quantity → 'Price, Quantity fields are missing'\n"
        "  All present → 'complete'\n\n"
        "Reply with the keyword(s) ONLY — no other text.\n\n"
        f"User message: {message}"
    )
}]
                response_ = self.client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=product_prompt
                )
                reply = response_.choices[0].message.content

                if reply == 'complete':
                    product_details=extract_product_details_ai(message[:-11])
                    user_details=Wallet.objects.filter(number_id=phone)
                    product_hash=hashlib.sha256(product_details["description"].encode()).hexdigest()

                    if user_details[0]:
                        print(product_details)
                        prod_obj=Product.objects.create(
                            title=product_details["title"],
                            description=product_details["description"],
                            quantity=product_details["quantity"],
                            image=img_url,
                            price=product_details["price"],
                            owner_name=user_details[0].title,
                            store_name=user_details[0].store_name,
                            is_paid=False,
                            product_hash=product_hash
                        )
                        return f"Stacks Payment Link Generated Below:\n\nhttp://localhost:5173/{product_hash}/checkout"
                    return "Got it"
                
                return reply
            return "Didn't quite get that could you send it again."

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
                    stx_private_key=res_data.json()["stxPrivateKey"],
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
    return WhatsappMultiMediaMessageHandler(payload).parse()


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


