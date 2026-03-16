from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from wallet.models import Wallet
from product.models import Product

from django.conf import settings
import requests
import stripe



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


# Create your views here.

processed_ids = set()
class StripeHandlerView(APIView):
    
    def get(self,request,*args,**kwargs):
        pass

    def post(self,request,*args,**kwargs):
        try:
            data = request.data
            print(data)
            amount = data.get('amount')
            wallet_obj=Wallet.objects.filter(title=data["product_data"]["owner_name"])
            prod_obj=Product.objects.get(product_hash=data['product_data']['product_hash'])

            
            if data["type"] == "PAID":
                msg=f"{prod_obj.purchase_by_first_name} {prod_obj.purchase_by_last_name} paid {amount} USDCx for {data['product_data']['quantity']} {data['product_data']['title']}"
               
                processed_ids.add(data['product_data']['product_hash'])
                if prod_obj.is_paid:
                     return Response({"Info":"Merchant Notified of Payment"})
                reply_whatsapp_message(msg=msg,to=wallet_obj[0].number_id)
                prod_obj.is_paid=True
                prod_obj.save()
                print("PAID")
                return Response({"Info":"Merchant Notified of Payment"})



            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": data["product_data"]["title"]},
                        "unit_amount": int(amount * 100),  # in clientSecret
                    },
                    "quantity": 1,
                }],
                mode="payment",
                ui_mode="embedded",  # 👈 this is the keyreturn_url
                return_url=f"http://localhost:5173/{data['product_data']['product_hash']}/checkout?session_id={wallet_obj[0].wallet_address}",
            )# in cents, e.g. 1000 = $10.00
            print(data,"RECV DATA")
            prod_obj.purchase_by_first_name=data["firstName"]
            prod_obj.purchase_by_last_name=data["lastName"]
            prod_obj.save()
            return Response({'clientSecret': session.client_secret})

        except stripe.error.StripeError as e:
            print(e)
            return Response({'error': str(e)}, status=400)


