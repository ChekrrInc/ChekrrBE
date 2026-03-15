from django.db import models

# Create your models here.

class Product(models.Model):
    title=models.CharField(max_length=255)
    image=models.CharField(max_length=255)
    price=models.CharField(max_length=255)
    quantity=models.IntegerField()
    owner_name=models.CharField(max_length=255)
    store_name=models.CharField(max_length=255)
    product_hash=models.CharField(max_length=255)
    is_paid=models.BooleanField()

