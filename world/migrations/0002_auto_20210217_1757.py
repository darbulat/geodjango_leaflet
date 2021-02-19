# Generated by Django 3.1.5 on 2021-02-17 17:57

import django.contrib.gis.db.models.fields
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('world', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='image',
            name='contacts',
            field=models.CharField(default='', max_length=200, verbose_name='Контакты'),
        ),
        migrations.AddField(
            model_name='image',
            name='image_file',
            field=models.ImageField(null=True, upload_to='lost_and_found', verbose_name='Изображение'),
        ),
        migrations.AlterField(
            model_name='image',
            name='date',
            field=models.DateField(default=django.utils.timezone.now, verbose_name='Дата'),
        ),
        migrations.AlterField(
            model_name='image',
            name='description',
            field=models.TextField(default='', null=True, verbose_name='Описание'),
        ),
        migrations.AlterField(
            model_name='image',
            name='id_out',
            field=models.IntegerField(null=True, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='image',
            name='link',
            field=models.CharField(max_length=200, null=True, verbose_name='Ссылка'),
        ),
        migrations.AlterField(
            model_name='image',
            name='point',
            field=django.contrib.gis.db.models.fields.PointField(null=True, srid=4326, verbose_name='Координаты'),
        ),
    ]
