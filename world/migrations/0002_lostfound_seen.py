# Generated by Django 3.1.5 on 2021-02-25 11:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('world', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='lostfound',
            name='seen',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]