from django.db import models

# Create your models here.
class Wallet(models.Model):
    title=models.CharField(max_length=255)
    secret_key=models.CharField(max_length=255)
    password=models.CharField(max_length=255)
    store_name=models.CharField(max_length=255)
    merchant_name=models.CharField(max_length=255)
    wallet_address=models.CharField(max_length=255)
    number_id=models.CharField(max_length=255)
    stx_private_key=models.CharField(max_length=255)

class BridgeIntent(models.Model):
    bridge_usdc_amount=models.CharField(max_length=255)
    target_stacks_address=models.CharField(max_length=255)
    is_executed=models.BooleanField()
    bridge_hash=models.CharField(max_length=255)



