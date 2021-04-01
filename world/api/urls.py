from django.urls import path, include

urlpatterns = [
    path('v1/', include('world.api.v1.urls')),
]