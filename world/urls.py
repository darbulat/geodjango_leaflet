from django.urls import path

from world import views

urlpatterns = [
    path('', views.index),
    path('upload/', views.upload_points, name='upload'),
]
