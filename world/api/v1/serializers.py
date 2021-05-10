from rest_framework import serializers

from world.models import Image


class ImageSerializer(serializers.HyperlinkedModelSerializer):
    type = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)

    class Meta:
        model = Image
        depth = 1
        fields = [
            'url', 'point', 'date', 'image_file', 'contacts',
            'description', 'type', 'email', 'radius',
            'intersected_objects',
        ]
