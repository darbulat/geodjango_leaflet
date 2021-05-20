from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from djangoProject import settings
from world.models import FOUND, Image
from world.notifications import send_email


@receiver(m2m_changed, sender='world.LostFound')
def send_email_notification(sender, instance, **kwargs):
    if instance.type == FOUND:
        for lost in instance.intersected_objects.all():
            send_email(
                subject='Найдены новые объекты соответсвующие Вашему объявлению',
                body=f'Для входа в личный кабинет объявления нажмите <a href="{settings.FRONTEND_SITE}/found/advertisement/?ad-uuid={instance.id}">сюда</a>',
                sender_email=settings.SENDER_EMAIL,
                receiver_email=lost.email,
                password=settings.EMAIL_PASSWORD,
            )


@receiver(post_save, sender=Image, dispatch_uid="send_notification")
def send_notifications(sender, instance: Image, **kwargs):
    if kwargs.get('created'):
        send_email(
            subject='Ваше объявление добавлено',
            body=f'Для входа в личный кабинет объявления нажмите <a href="{settings.FRONTEND_SITE}/found/advertisement/?ad-uuid={instance.id}">сюда</a>',
            sender_email=settings.SENDER_EMAIL,
            receiver_email=instance.email,
            password=settings.EMAIL_PASSWORD,
        )
