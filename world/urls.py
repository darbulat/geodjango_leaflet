from django.urls import path

from world import views

urlpatterns = [
    path('', views.index, name='upload'),
]
