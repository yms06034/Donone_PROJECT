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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
