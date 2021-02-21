from django.urls import path

from world import views

urlpatterns = [
    path('upload/', views.upload, name='upload'),
    path('found/', views.send_found_object),
    path('lost/', views.send_lost_object),
    path('', views.search, name='search'),
]
