from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('api/clients/', views.client_collection, name='client-list'),
    path('api/clients/<int:pk>/', views.client_detail, name='client-detail'),
    path('health/', views.health, name='health'),
]
