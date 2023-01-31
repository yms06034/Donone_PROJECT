from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Test(models.Model):
    pass

class Ably_token(models.Model):
    ably_id = models.CharField(max_length=100)
    ably_pw = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
class Cafe24(models.Model):
    cafe24_id = models.CharField('아이디', max_length=200)
    cafe24_pw = models.CharField('비밀번호', max_length=200)
    cafe24_clientid = models.CharField(max_length=200 , default='none')
    cafe24_client_secret = models.CharField(max_length=200, default='none')
    cafe24_mallid = models.CharField(max_length=200, default='none')
    cafe24_encode_csrf_token = models.CharField(max_length=50 , null=True)
    cafe24_redirect_uri = models.CharField(max_length=200 , default='none')
    service_key = models.CharField(max_length=200, default='none')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    

class AblySalesInfo(models.Model):
    paymentDate = models.CharField(max_length=50)
    productOrderNumber = models.IntegerField()
    orderNumber = models.CharField(max_length=50)
    productName = models.CharField(max_length=150)
    options = models.CharField(max_length=50)
    total = models.IntegerField()
    orderName = models.CharField(max_length=20)
    phoneNumber = models.CharField(max_length=30)
    orderStatus = models.CharField(max_length=20)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

class AblyProductInfo(models.Model):
    productNumber = models.CharField(max_length=20)
    productName = models.CharField(max_length=150)
    price = models.IntegerField()
    discountPeriod = models.CharField(max_length=20, default='none')
    discountPrice = models.CharField(max_length=50)
    registrationDate = models.CharField(max_length=50)
    statusDisplay = models.CharField(max_length=10)
    stock = models.CharField(max_length=10)
    totalReview = models.IntegerField()
    parcel = models.CharField(max_length=10)
    returnShippingCost = models.IntegerField()
    extraShippingCost = models.IntegerField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)