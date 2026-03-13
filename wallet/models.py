from django.db import models

# Create your models here.
class Wallet(models.Model):
    title=models.CharField(max_length=255,blank=True,null=True)
    secret_key=models.CharField(max_length=255)
    password=models.CharField(max_length=255)
    store_name=models.CharField(max_length=255,blank=True,null=True)
    merchant_name=models.CharField(max_length=255,blank=True,null=True)
    wallet_address=models.CharField(max_length=255,blank=True,null=False)
    number_id=models.CharField(max_length=255,blank=True,null=True)



