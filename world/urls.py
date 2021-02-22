from django.urls import path

from world import views
from world.views import ImageUpdate, ImageDelete, ImageIntersect

urlpatterns = [
    path('upload/', views.upload, name='upload'),
    path('found/', views.send_found_object, name='found'),
    path('lost/', views.send_lost_object, name='lost'),
    path('<uuid:pk>/', ImageIntersect.as_view(), name='image_intersect'),
    path('<uuid:pk>/update', ImageUpdate.as_view(success_url='update'), name='image_update'),
    path('<uuid:pk>/delete', ImageDelete.as_view(success_url='/'), name='image_delete'),
    path('', views.search, name='search'),
]
