from django.contrib.gis.db import models
from django.utils import timezone


class Image(models.Model):

    id_out = models.IntegerField(null=True, blank=True, verbose_name='ID')
    point = models.PointField(null=True, verbose_name='Координаты', srid=4326)
    date = models.DateField(verbose_name='Дата', default=timezone.now)
    link = models.CharField(null=True, blank=True, max_length=200, verbose_name='Ссылка')
    image_file = models.ImageField(null=True, blank=True, upload_to='lost_and_found',
                                   verbose_name='Изображение')
    contacts = models.CharField(max_length=200, verbose_name='Контакты',
                                default='')
    description = models.TextField(null=True, verbose_name='Описание', default='')
