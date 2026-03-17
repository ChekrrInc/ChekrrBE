import os
import json
from datetime import datetime
from django.http import HttpResponse
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from .utils import ChekrrBot,parse_twilio_dict,reply_whatsapp_message,fetch_twilio_image

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
