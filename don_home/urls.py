from django.urls import path
from don_home import views

urlpatterns = [
    path('', views.index, name='index'),
    path('signup/', views.signup, name="signup"),
    path('login/', views.login, name="login"),
    path('logout/', views.logout, name="logout"),
    path('activate/<str:uid64>/<str:token>/', views.activate, name="activate"),
    path('api/checkeusername', views.checkeusername, name="checkeusername")
]
