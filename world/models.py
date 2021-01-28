from django.contrib.gis.db import models


class Image(models.Model):

    id_out = models.IntegerField()
    point = models.PointField(null=True)
    date = models.DateField()
    link = models.CharField(max_length=200)
    description = models.TextField(null=True)
