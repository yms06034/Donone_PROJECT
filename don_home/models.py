from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Cafe24(models.Model):
    cafe24_id = models.CharField('아이디', max_length=50, null=False)
    cafe24_pw = models.CharField('비밀번호', max_length=50, null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    

    