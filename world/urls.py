from django.urls import path

from world import views

urlpatterns = [
    path('', views.index, name='upload'),
    path('<int:id_out>/', views.get_location, name='location'),
]
