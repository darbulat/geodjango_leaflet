from captcha.fields import CaptchaField
from django.contrib.gis import forms

from world.models import Image


class FoundObjectForm(forms.ModelForm):
    captcha = CaptchaField(
        error_messages={"invalid": "Неправильно введена капча"},
        label='Капча',
    )
    point = forms.PointField(
        widget=forms.OSMWidget(
            attrs={'default_lat': 55.786612514494706, 'default_lon': 49.129486083984375, 'map_srid': 4326}
        ),
        error_messages={"required": "Не указаны координаты"},
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
    def __init__(self, *args, **kwargs):
        super(LostObjectForm, self).__init__(*args, **kwargs)
        self.fields['radius'].disabled = True

    captcha = CaptchaField(
        error_messages={"invalid": "Неправильно введена капча"},
        label='Капча',
    )
    multi_point = forms.MultiPointField(
        widget=forms.OSMWidget(
            attrs={'default_lat': 55.786612514494706, 'default_lon': 49.129486083984375, 'map_srid': 4326}
        ),
        error_messages={"required": "Не указаны координаты"},
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
