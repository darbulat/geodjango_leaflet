from django.contrib.gis import forms

from world.models import Image


class FoundObjectForm(forms.ModelForm):
    point = forms.PointField(
        widget=forms.OSMWidget(
            attrs={'default_lat': 55.786612514494706, 'default_lon': 49.129486083984375, 'map_srid': 4326}
        ),
        label='Координаты',
    )

    class Meta:
        model = Image
        fields = [
            'image_file',
            'date',
            'email',
            'contacts',
            'description',
        ]


class LostObjectForm(forms.ModelForm):
    multi_point = forms.MultiPointField(
        widget=forms.OSMWidget(
            attrs={'default_lat': 55.786612514494706, 'default_lon': 49.129486083984375, 'map_srid': 4326}
        ),
        label='Координаты',
    )

    class Meta:
        model = Image
        fields = [
            'image_file',
            'date',
            'email',
            'contacts',
            'description',
            'radius',
        ]
