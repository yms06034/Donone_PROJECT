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
    path('api/ablydata/', views.get_ably_data, name='getablydata'),
    path('user/ably/' , views.ably, name='ably'),
    path('user/data/' , views.usertoken, name='usertoken'),
    path('user/cafe24/' , views.cafe24, name='cafe24'),
    path('user/dashboard/' , views.dashboard, name='dashboard'),
    path('api/ablyproduct/', views.ablyproduct_api),
    path('api/ablysales/', views.ablysales_api),
    path('api/cafe24all/', views.cafe24all_api),
    path('user/ably/delete', views.delete_ably_data, name='ably_delete'),
    path('user/cafe24/delete', views.delete_cafe24_data, name='cafe24_delete')
]
