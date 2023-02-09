from django.test import TestCase
from sqlalchemy import create_engine
from cp2_don.don_settings import MYSQL_CONN
from don_home.models import Cafe24

# Create your tests here.
engine = create_engine(MYSQL_CONN)

cafe24 = Cafe24.objects.select_related('user').values(
    'cafe24_id',
    'cafe24_pw',
    'cafe24_clientid',
    'cafe24_client_secret',
    'cafe24_mallid',
    'cafe24_encode_csrf_token',
    'cafe24_redirect_uri',)

print(cafe24)