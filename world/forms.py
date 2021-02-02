from django import forms

from world.models import Image


class FoundObjectForm(forms.ModelForm):

    is_true_location = forms.NullBooleanField()

    class Meta:
        model = Image
        fields = [
            'image_file',
            'contacts',
            'description',
        ]
