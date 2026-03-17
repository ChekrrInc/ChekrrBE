
from django.urls import path
from .views import StripeHandlerView,OnChainPaymentView


urlpatterns=[
    path("stripe/",StripeHandlerView.as_view()),
    path("onchain_payment/",OnChainPaymentView.as_view())
]
