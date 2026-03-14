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



