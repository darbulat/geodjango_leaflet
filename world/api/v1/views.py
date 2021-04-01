from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework import permissions
from rest_framework_gis.filters import DistanceToPointOrderingFilter

from .serializers import ImageSerializer
from world.models import Image


class ImageViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Images to be viewed or edited.
    """
    queryset = Image.objects.all().order_by('-date')
    serializer_class = ImageSerializer
    permission_classes = [permissions.IsAdminUser]
    distance_ordering_filter_field = 'point'
    filterset_fields = {
        'type': ['exact'],
        'date': ['gte', 'lte', 'exact', 'gt', 'lt'],
    }
    filter_backends = (DistanceToPointOrderingFilter, DjangoFilterBackend)
