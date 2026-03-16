from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import ProductSerializer
from .models import Product

# Create your views here.

class ProductAPIView(APIView):
    serializer=ProductSerializer

    def get(self,request,*args,**kwargs):
        return Response({ "inDev":True})

    def post(self,request,*args,**kwargs):
        data=request.data
        print(data)

        if "chekrrId" not in data:
            return Response({"Error":"chekrrId Not In Function"})

        product=Product.objects.filter(product_hash=data["chekrrId"]) 
        res=self.serializer(product[0])
        return Response({ "productData":res.data})

