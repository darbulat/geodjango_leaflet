from django.urls import path
from plots import views


urlpatterns = [
    path('', views.index, name='index'),
]
