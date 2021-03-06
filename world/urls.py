from django.urls import path, include

from world import views

urlpatterns = [
    path('api/', include('world.api.urls')),
    path('upload/', views.BulkUpload.as_view(), name='upload'),
    path('found/', views.send_found_object, name='found'),
    path('lost/', views.send_lost_object, name='lost'),
    path('search/', views.SearchPoints.as_view(), name='search'),
    path('send_notifications/', views.SendNotifications.as_view(), name='send_notifications'),
    path('my/', views.MyAd.as_view(), name='my_ad'),
    path('<uuid:pk>/', views.ImageIntersect.as_view(), name='image_intersect'),
    path('<uuid:pk>/update', views.ImageUpdate.as_view(success_url='update'), name='image_update'),
    path('<uuid:pk>/delete', views.ImageDelete.as_view(success_url='/'), name='image_delete'),
    path('', views.Index.as_view(), name='index')
]
