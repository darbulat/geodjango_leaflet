from django import forms

from world.models import Image


class FoundObjectForm(forms.ModelForm):

    class Meta:
        model = Image
        fields = [
            'image_file',
            'contacts',
            'description',
        ]
