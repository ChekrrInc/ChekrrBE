from django.urls import path
from .views import BotWalletView

urlpatterns=[
    path("",BotWalletView.as_view(),name="bot")
]
