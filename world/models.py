import datetime
import os
from tempfile import NamedTemporaryFile
from typing import Tuple, Dict, List
from urllib.request import urlopen

from django.contrib.gis import forms
from django.contrib.gis.db import models
from django.contrib.gis.geos import MultiPoint
from django.contrib.gis.measure import D
from django.core.files import File
from django.utils import timezone

import uuid

from djangoProject import settings
from world import constants

LOST = 'lost'
FOUND = 'found'


class AbstractUUID(models.Model):
    """ Абстрактная модель для использования UUID в качестве PK."""

    # Параметр blank=True позволяет работать с формами, он никогда не
    # будет пустым, см. метод save()

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class Image(AbstractUUID):
    CHOICES = (
        (LOST, LOST),
        (FOUND, FOUND),
    )
    point = models.MultiPointField(null=True, verbose_name='Координаты',
                                   srid=4326, unique=True)
    point.form_class.widget = forms.OSMWidget(
        attrs={'map_srid': 4326}
    )
    date = models.DateField(verbose_name='Дата', default=timezone.now)
    image_file = models.ImageField(null=True, blank=True,
                                   upload_to='lost_and_found',
                                   verbose_name='Изображение')
    image_url = models.URLField(null=True)
    contacts = models.CharField(max_length=200, verbose_name='Контакты',
                                default='', null=True, blank=True)
    description = models.TextField(null=True, blank=True,
                                   verbose_name='Описание', default='')
    type = models.CharField(null=False, blank=False, max_length=10, default='',
                            choices=CHOICES)
    active = models.BooleanField(default=False)
    email = models.EmailField(null=True, blank=True, default='')
    radius = models.FloatField(null=False, blank=False, default=50)

    def save(self, *args, **kwargs):
        if not self.image_url and not self.image_file:
            self.image_url = settings.SITE + '/media/blank_image.png'
        if self.image_url and not self.image_file:
            if self.image_url.startswith('/media'):
                self.image_url = settings.SITE + self.image_url
            img_temp = NamedTemporaryFile(delete=True)
            img_temp.write(urlopen(self.image_url).read())
            img_temp.flush()
            filename = os.path.basename(self.image_url)
            self.image_file.save(filename, File(img_temp))
        super(Image, self).save(*args, **kwargs)
        if self.image_file:
            self.image_url = self.image_file.url
            super(Image, self).save(*args, **kwargs)

    @classmethod
    def get_objects(cls,
                    multi_point: MultiPoint,
                    radius: float,
                    obj_type: str,
                    fields: list = (),
                    from_date: datetime.date = None,
                    to_date: datetime.date = None,
                    active: bool = None) -> List[Dict]:
        if from_date is None:
            from_date = datetime.date.today() - datetime.timedelta(days=1)
        if to_date is None:
            to_date = datetime.date.today() + datetime.timedelta(days=1)
        date_range = (from_date, to_date)
        query = dict(
            point__distance_lte=(multi_point, D(m=radius)),
            date__range=date_range,
            type=obj_type
        )
        if active is not None:
            query.update(active=active)
        images = cls.objects.filter(**query).values(*fields)
        return list(images)

    def get_intersected_objects(self, active: bool = None, fields: list = ()):
        query = dict(
            point__distance_lte=(self.point, D(m=self.radius)),
            date__gte=self.date,
        )
        query.update(type=LOST if self.type == FOUND else FOUND)
        if active is not None:
            query.update(active=active)
        images = Image.objects.filter(**query).values(*fields)
        return list(images)


class LostFound(models.Model):
    lost = models.ForeignKey(Image, on_delete=models.CASCADE, related_name=LOST)
    found = models.ForeignKey(Image, on_delete=models.CASCADE,
                              related_name=FOUND)
