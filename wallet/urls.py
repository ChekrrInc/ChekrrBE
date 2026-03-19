from django.urls import path
from .views import BotWalletView,BridgeIntentView

urlpatterns=[
    path("",BotWalletView.as_view(),name="bot"),
    path("bridgeintent/",BridgeIntentView.as_view())
]
