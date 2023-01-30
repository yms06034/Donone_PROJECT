from django.urls import path
from don_home import views

app_name = 'app'

urlpatterns = [
    path('', views.index, name='index'),
    path('signup/', views.signup, name="signup"),
    path('login/', views.login, name="login"),
    path('logout/', views.logout, name="logout"),
    path('activate/<str:uid64>/<str:token>/', views.activate, name="activate"),
    path('api/checkeusername', views.checkeusername, name="checkeusername"),
    path('user/ably' , views.ably, name='ably'),
    path('user/cafe24' , views.cafe24, name='cafe24')
]
