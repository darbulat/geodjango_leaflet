from rest_framework import serializers

from world.models import Image


class ImageSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Image
        depth = 1
        fields = [
            'url', 'point', 'date', 'image_file', 'contacts',
            'description', 'type', 'active', 'email', 'radius',
            'intersected_objects',
        ]
