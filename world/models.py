from django.contrib.gis.db import models


class Image(models.Model):

    id_out = models.IntegerField()
    point = models.PointField()
    date = models.DateField()
    link = models.CharField(max_length=100)
