from django.db import models

# Create your models here.

class Product(models.Model):
    title=models.CharField(max_length=255)
    description=models.TextField(null=True,blank=True)
    image=models.TextField()
    price=models.CharField(max_length=255)
    quantity=models.IntegerField()
    owner_name=models.CharField(max_length=255)
    store_name=models.CharField(max_length=255)
    product_hash=models.CharField(max_length=255)
    is_paid=models.BooleanField()
    purchase_by_first_name=models.CharField(max_length=255,null=True,blank=True)
    purchase_by_last_name=models.CharField(max_length=255,null=True,blank=True)

