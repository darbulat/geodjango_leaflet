import datetime
from typing import Tuple, Dict, List, Any, Union

from django.contrib.gis import forms
from django.contrib.gis.db import models
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import MultiPoint
from django.contrib.gis.measure import D
from django.db.models import F
from django.utils import timezone
from PIL import Image as PILImage

import uuid

LOST = 'lost'
FOUND = 'found'


class AbstractUUID(models.Model):
    """ Абстрактная модель для использования UUID в качестве PK."""

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
    date = models.DateField(verbose_name='Дата', default=timezone.now().date())

    _date_path = datetime.date.today().strftime("%Y/%m/%d")

    image_file = models.ImageField(null=True, blank=True,
                                   upload_to=_date_path,
                                   verbose_name='Изображение')
    image_url = models.URLField(null=True)
    contacts = models.CharField(max_length=200, verbose_name='Контакты',
                                default='', null=True, blank=True)
    description = models.TextField(null=True, blank=True,
                                   verbose_name='Описание', default='')
    type = models.CharField(null=False, blank=False, max_length=10, default='',
                            choices=CHOICES)
    active = models.BooleanField(default=True)
    email = models.EmailField(null=True, blank=True, default='')
    radius = models.FloatField(null=False, blank=False, default=50)
    intersected_objects = models.ManyToManyField(
        'self', blank=True, through='LostFound', symmetrical=True
    )

    def save(self, *args, **kwargs):
        kwargs = {}
        if self.image_file:
            super(Image, self).save(*args, **kwargs)
            self.image_url = self.image_file.url
            compressed = PILImage.open(self.image_file.path)
            compressed.save(self.image_file.path, quality=20, optimize=True)
        if self.point:
            intersected_images = self.get_intersected_objects()
            self.intersected_objects.add(*intersected_images)
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

    def get_intersected_objects(self, active: bool = None,
                                fields: list = (),
                                seen: bool = False) -> Union[Tuple[Any, Any], list]:
        query = dict()
        yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
        if self.type == LOST:
            query.update(point__distance_lte=(self.point, D(m=self.radius)),
                         type=FOUND, date__gte=self.date)
            intersected_images = LostFound.objects.filter(
                lost_id=self.pk, seen__lte=yesterday, seen__isnull=False
            ).values_list('found_id', flat=True)
        else:
            query.update(distance__lte=F('radius'),
                         type=LOST,
                         date__lte=self.date)
            intersected_images = LostFound.objects.filter(
                found_id=self.pk,
                seen__lte=yesterday
            ).values_list('lost_id', flat=True)
        if active is not None:
            query.update(active=active)
        if seen:
            new_images = Image.objects.annotate(
                distance=Distance('point', self.point)
            ).filter(
                **query
            ).exclude(
                id__in=intersected_images
            ).order_by('date').values(*fields)
            images = Image.objects.annotate(
                distance=Distance('point', self.point)
            ).filter(
                id__in=intersected_images,
                **query
            ).order_by('date').values(*fields)
            return list(images), list(new_images)
        else:
            images = Image.objects.annotate(
                distance=Distance('point', self.point)
            ).filter(**query).order_by('date')
            if fields:
                images = images.values(*fields)
            return list(images)


class LostFound(models.Model):
    lost = models.ForeignKey(Image, on_delete=models.CASCADE, related_name=LOST)
    found = models.ForeignKey(Image, on_delete=models.CASCADE,
                              related_name=FOUND)
    seen = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = (("lost", "found"),)
