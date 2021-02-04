from django import forms


class LineForm(forms.Form):
    start_point = forms.CharField(widget=forms.TextInput(attrs={'size': 5}))
    end_point = forms.CharField(widget=forms.TextInput(attrs={'size': 5}))
    direction = forms.CharField(required=False, widget=forms.HiddenInput())
    rhumb = forms.IntegerField(widget=forms.TextInput(attrs={'size': 5}))
    distance = forms.IntegerField(widget=forms.TextInput(attrs={'size': 8}))
    points = forms.CharField(
        max_length=300, required=False, widget=forms.HiddenInput())
    prev_forms = forms.CharField(required=False, widget=forms.HiddenInput())


class PointForm(forms.Form):
    num = forms.CharField(required=False, initial='0', disabled=True, widget=forms.TextInput(attrs={'size': 5}))
    long = forms.FloatField(widget=forms.TextInput(attrs={'size': 11}))
    lat = forms.FloatField(widget=forms.TextInput(attrs={'size': 11}))


class ShapeForm(forms.Form):
    linear_ring = forms.CharField(required=True, widget=forms.HiddenInput())
