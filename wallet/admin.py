from django.contrib import admin
from .models import Wallet,BridgeIntent

# Register your models here.
admin.site.register(Wallet)
admin.site.register(BridgeIntent)
