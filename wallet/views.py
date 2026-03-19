import os
import json
from datetime import datetime
from django.http import HttpResponse
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from .utils import ChekrrBot,parse_twilio_dict,reply_whatsapp_message,fetch_twilio_image
from .models import BridgeIntent,Wallet

import requests


chekrrbot=ChekrrBot()
processed_ids = set()

class BotWalletView(APIView):

    def get(self, request, *args, **kwargs):
        mode      = request.query_params.get("hub.mode")
        token     = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge")

        if mode == "subscribe" and token == settings.WHATSAPP_BUSINESS_ACCESS_TOKEN:
            print("WEBHOOK VERIFIED")
            return HttpResponse(challenge, content_type="text/plain", status=200)

        return HttpResponse("Forbidden", status=403)

    def post(self, request, *args, **kwargs):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        res=parse_twilio_dict(request.data)

        print(res)

        if res is None:
            return HttpResponse(status=403)

        if "imageUrl" in res:
           response=chekrrbot.reply(phone=res["phone"],message=res["message"],id=res["id"],img_url=fetch_twilio_image(res["imageUrl"]))
           reply_whatsapp_message(to=res['phone'],msg=response)
        else:
           response=chekrrbot.reply(phone=res["phone"],message=res["message"],id=res["id"],img_url='')
           reply_whatsapp_message(to=res['phone'],msg=response)
    
        return HttpResponse(status=200)


class BridgeIntentView(APIView):

    def get(self,request,*args,**kwargs):
        pass

    def post(self,request,*args,**kwargs):
        data=request.data
        
        bridgeIntent=BridgeIntent.objects.get(bridge_hash=data["bridgeIntentId"])
        masterWallet=Wallet.objects.filter(title="Master Wallet")

        if "isExecuted" in data:
            wallet_obj=Wallet.objects.filter(wallet_address=data["stacksAddress"])
            print(wallet_obj)
            res_data=requests.post("http://localhost:8080/wallet/transfer",json={
                        "usdcxAmount":bridgeIntent.bridge_usdc_amount,
                        "recipientAddress":wallet_obj[0].wallet_address,
                        "senderPrivateKey":masterWallet[0].stx_private_key
            })

            msg=f"Successfully bridged {bridgeIntent.bridge_usdc_amount} ETH Sepolia USDC to  {bridgeIntent.bridge_usdc_amount} USDCx on Stacks\nTransaction Hash:\n\nhttps://explorer.hiro.so/txid/{res_data.json()['txid']}?chain=testnet\n\nPowered by USDC xReserve Protocol"
            reply_whatsapp_message(msg=msg,to=wallet_obj[0].number_id)
            bridgeIntent.is_executed=True
            bridgeIntent.save()
            return Response({"Info":"User Notified"}) 


       
        return Response({ "BridgeIntentData":{
            "usdcAmount":bridgeIntent.bridge_usdc_amount,
            "recvStacksAddress":bridgeIntent.target_stacks_address
        }})
