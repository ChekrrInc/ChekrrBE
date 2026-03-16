
from django.urls import path
from .views import StripeHandlerView


urlpatterns=[
    path("stripe/",StripeHandlerView.as_view())
]
