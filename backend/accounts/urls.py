from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('users/', views.users_list_view, name='users_list'),
    path('register/', views.register_view, name='register'),
    path('delete/', views.delete_user_view, name='delete_user'),
    path('update/', views.update_user_view, name='update_user'),
]