from django.contrib.gis.db import models
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
    point = models.MultiPointField(null=True, verbose_name='Координаты', srid=4326)
    date = models.DateField(verbose_name='Дата', default=timezone.now)
    link = models.CharField(null=True, blank=True, max_length=200, verbose_name='Ссылка')
    image_file = models.ImageField(null=True, blank=True, upload_to='lost_and_found',
                                   verbose_name='Изображение')
    contacts = models.CharField(max_length=200, verbose_name='Контакты',
                                default='')
    description = models.TextField(null=True, blank=True, verbose_name='Описание', default='')
    type = models.CharField(null=False, blank=False, max_length=10, default='', choices=CHOICES)
    active = models.BooleanField(default=False)
    email = models.EmailField(null=False, blank=False)
    radius = models.FloatField(null=False, blank=False, default=50)
