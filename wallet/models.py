from django.db import models

# Create your models here.
class Wallet(models.Model):
    title=models.CharField(max_length=255,blank=True,null=True)
    secretkey=models.CharField(max_length=255)
    password=models.CharField(max_length=255)
    store_name=models.CharField(max_length=255,blank=True,null=True)
    merchant_name=models.CharField(max_length=255,blank=True,null=True)


