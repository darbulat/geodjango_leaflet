import datetime
import os
from tempfile import NamedTemporaryFile
from urllib.request import urlopen

from django.contrib.gis.db import models
from django.core.files import File
from django.utils import timezone

import uuid

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
    point = models.MultiPointField(null=True, verbose_name='Координаты', srid=4326, unique=True)
    date = models.DateField(verbose_name='Дата', default=timezone.now)
    image_file = models.ImageField(null=True, blank=True, upload_to='lost_and_found',
                                   verbose_name='Изображение')
    image_url = models.URLField(null=True)
    contacts = models.CharField(max_length=200, verbose_name='Контакты',
                                default='')
    description = models.TextField(null=True, blank=True, verbose_name='Описание', default='')
    type = models.CharField(null=False, blank=False, max_length=10, default='', choices=CHOICES)
    active = models.BooleanField(default=False)
    email = models.EmailField(null=False, blank=False)
    radius = models.FloatField(null=False, blank=False, default=50)

    def save(self, *args, **kwargs):
        if self.image_url and not self.image_file:
            img_temp = NamedTemporaryFile(delete=True)
            img_temp.write(urlopen(self.image_url).read())
            img_temp.flush()
            self.image_file.save(f"image_{datetime.datetime.now()}.jpeg", File(img_temp))
        super(Image, self).save(*args, **kwargs)
        self.image_url = self.image_file.url
        super(Image, self).save(*args, **kwargs)


class LostFound(models.Model):
    lost = models.ForeignKey(Image, on_delete=models.CASCADE, related_name=LOST)
    found = models.ForeignKey(Image, on_delete=models.CASCADE, related_name=FOUND)
