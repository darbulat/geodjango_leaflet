from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from djangoProject import settings
from djangoProject.settings import SENDER_EMAIL, EMAIL_PASSWORD
from world.models import FOUND
from world.notifications import send_email


@receiver(m2m_changed, sender='world.LostFound')
def send_email_notification(sender, instance, **kwargs):
    if instance.type == FOUND:
        for lost in instance.intersected_objects.all():
            send_email(
                subject='Найдены новые вещи',
                body=f'Найдены вещи соответсвующие <a href="{settings.SITE}/{lost.pk}">вашему объявлению</a>',
                sender_email=SENDER_EMAIL,
                receiver_email=lost.email,
                password=EMAIL_PASSWORD,
            )
