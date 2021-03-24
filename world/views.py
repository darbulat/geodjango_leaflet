import csv
import datetime
import io
import json

from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import Point, MultiPoint
from django.db import IntegrityError
from django.db.transaction import atomic
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import UpdateView, DeleteView, TemplateView

from djangoProject import settings
from djangoProject.settings import (
    EMAIL_PASSWORD,
    RECEIVER_EMAIL,
    SENDER_EMAIL,
    OPENCAGE_KEY,
    IS_SEND_EMAIL,
)
from world.forms import FoundObjectForm, LostObjectForm
from world.helpers import parse_date_from_str, get_message, \
    update_images_for_context
from world.models import Image, FOUND, LOST, LostFound
from world.notifications import send_email


@method_decorator(login_required, name='get')
class BulkUpload(View):
    def get(self, request, *args, **kwargs):
        return render(request, "world/upload.html", {})

    def post(self, request, *args, **kwargs):
        message = ''
        if file := request.FILES.get("csv_file"):

            csv_file = file.read().decode("utf-8")
            reader = csv.reader(io.StringIO(csv_file), delimiter=";",
                                quotechar="|")
            counter_of_new_objects = 0
            try:
                for lat, long, date, image_url, description, contacts, email in reader:
                    try:
                        year, month, day = parse_date_from_str(date)
                        date = datetime.date(year=year, month=month, day=day)
                        point = MultiPoint(Point(x=float(long), y=float(lat)))
                        image = Image(
                            point=point,
                            date=date,
                            image_url=image_url,
                            description=description,
                            contacts=contacts,
                            type=FOUND,
                            email=email,
                        )
                        try:
                            image.save()
                        except UnicodeEncodeError:
                            return HttpResponseBadRequest(
                                "Название файла должно быть на латинице")
                        counter_of_new_objects += 1
                    except ValueError:
                        pass
                    except IntegrityError:
                        message = "Вы пытаетесь загрузить объекты с " \
                                  "одинаковыми координатами, \n" \
                                  "исправьте координаты и повторите загрузку"
                        break
                    except Exception as e:
                        message = str(e)
                        break
            except ValueError:
                pass
            if not message:
                message = f"Новых записей: {counter_of_new_objects}\n"

        else:
            message = 'Необходимо прикрепить файл'
        return render(
            request,
            "world/upload.html",
            {
                "message": message
            },
        )


def get_search_context(radius, obj_type=None, from_date=None,
                       to_date=None, points=None):
    points_list = []
    multi_points = MultiPoint(Point(55.752071, 48.744513))
    if points:
        points_list = json.loads(points)
        multi_points = MultiPoint(
            *[Point(x=long, y=lat) for long, lat in points_list], srid=4326
        )
    kwargs = dict(
        multi_point=multi_points,
        radius=radius,
        obj_type=obj_type,
        fields=['point', 'active', 'date', 'image_url', 'description',
                'contacts']
    )
    if from_date:
        kwargs.update(from_date=datetime.date.fromisoformat(from_date))
    if to_date:
        kwargs.update(to_date=datetime.date.fromisoformat(to_date))
    images = Image.get_objects(**kwargs)

    image_count, not_active_image_count = update_images_for_context(images)

    message = get_message(image_count)
    message = message + f' из них на модерации: {not_active_image_count}'
    return {
        "images": images,
        "from_date": from_date,
        "to_date": to_date,
        "radius": float(radius),
        "points": points_list,
        "message": message,
        "opencage_key": OPENCAGE_KEY,
    }


@method_decorator(login_required, name='get')
class SearchPoints(View):

    def get(self, request, *args, **kwargs):
        return render(
            request, "world/search.html",
            dict(opencage_key=OPENCAGE_KEY, images=[])
        )

    def post(self, request, *args, **kwargs):
        from_date = request.POST.get("from_date")
        to_date = request.POST.get("to_date")
        if radius := request.POST.get("radius"):
            radius = float(radius)
        else:
            radius = 50
        obj_type = LOST if request.POST.get("is-lost") else FOUND
        points = request.POST.get("points")
        context = get_search_context(
            radius=radius,
            obj_type=obj_type,
            from_date=from_date,
            to_date=to_date,
            points=points,
        )
        return render(request, "world/search.html", context)


@login_required(login_url="/admin")
@atomic
def send_found_object(request):
    if request.method == "POST":
        form = FoundObjectForm(request.POST, request.FILES)
        if form.is_valid():
            description = form.cleaned_data.get("description")
            contacts = form.cleaned_data.get("contacts")
            point: Point = form.cleaned_data.get("point")
            date = form.cleaned_data.get("date")
            email = form.cleaned_data.get('email')
            file = form.files.get("image_file")

            obj_type = FOUND
            point.transform(4326)
            multi_point = MultiPoint(point)
            obj = Image(
                contacts=contacts,
                description=description,
                point=multi_point,
                image_file=file,
                date=date,
                email=email,
                type=obj_type,
            )
            try:
                obj.save()
            except UnicodeEncodeError:
                return HttpResponseBadRequest(
                    "Название файла должно быть на латинице"
                )
            except IntegrityError:
                return HttpResponseBadRequest(
                    "Координаты в точности совпадают с ранее введенной "
                    "координатой, поменяйте координаты и повторите снова"
                )
            if IS_SEND_EMAIL:
                body = f"UUID объекта: {obj.id}"
                send_email(subject='Найден новый объект',
                           body=body, fp=file,
                           sender_email=SENDER_EMAIL,
                           receiver_email=RECEIVER_EMAIL,
                           password=EMAIL_PASSWORD)
            return HttpResponse(
                content="Ваше сообщение отправлено администраторам, "
                        "спасибо за бдительность!"
                        f'Ссылка на личный кабинет: <a href="{settings.SITE}/{obj.id}">{obj.id}</a>'
            )
        else:
            return render(request, "world/send_found.html", {"form": form})

    else:
        form = FoundObjectForm()
        return render(request, "world/send_found.html", {"form": form})


@login_required(login_url="/admin")
@atomic
def send_lost_object(request):
    form = LostObjectForm(request.POST, request.FILES)

    if request.method == "POST":

        if form.is_valid():
            description = form.cleaned_data.get("description")
            contacts = form.cleaned_data.get("contacts")
            multi_point: MultiPoint = form.cleaned_data.get("multi_point")
            date = form.cleaned_data.get("date")
            email = form.cleaned_data.get('email')
            radius = form.cleaned_data.get("radius")
            file = form.files.get("image_file")
            obj_type = LOST
            multi_point.transform(4326)
            kwargs = dict(contacts=contacts,
                          description=description,
                          point=multi_point,
                          date=date,
                          email=email,
                          type=obj_type,
                          image_file=file,
                          radius=radius)

            obj = Image(**kwargs)
            try:
                obj.save()
            except UnicodeEncodeError:
                return HttpResponseBadRequest(
                    "Название файла должно быть на латинице"
                )
            except IntegrityError:
                return HttpResponseBadRequest(
                    "Координаты в точности совпадают с ранее введенной "
                    "координатой, поменяйте координаты и повторите снова"
                )
            send_email(
                subject='Ваше объявление скоро будет добавлено',
                body=f'Ссылка на личный кабинет: <a href="{settings.SITE}/{obj.id}">{obj.id}</a>',
                sender_email=SENDER_EMAIL,
                receiver_email=obj.email,
                password=EMAIL_PASSWORD,
            )

            if IS_SEND_EMAIL:
                body = f"UUID объекта: {obj.id}"
                send_email(subject='Найден новый объект',
                           body=body,
                           sender_email=SENDER_EMAIL,
                           receiver_email=RECEIVER_EMAIL,
                           password=EMAIL_PASSWORD)
            return HttpResponse(
                content=f"Ваше сообщение отправлено на модерацию<br>"
                        f"По <a href='/{obj.id}'>этой ссылке</a> доступно ваше объявление"
            )
        else:
            return render(request, "world/send_found.html", {"form": form})

    else:
        form = LostObjectForm()
        return render(request, "world/send_lost.html", {"form": form})


class ImageUpdate(UpdateView):
    model = Image
    fields = ['image_file', 'point', 'date', 'contacts', 'email', 'radius',
              'description']


class ImageDelete(DeleteView):
    model = Image


@method_decorator(login_required, name='get')
class ImageIntersect(View):

    def get(self, request, *args, **kwargs):
        image_id = kwargs.get('pk')
        lost_obj = Image.objects.filter(pk=image_id).first()
        found_images = []
        new_images = []
        radius = 50
        lost_points = []
        if not lost_obj:
            message = "Объявление не найдено"
        else:
            radius = lost_obj.radius
            lost_points = list(
                dict(x=point.x, y=point.y) for point in lost_obj.point)
            fields = ['point', 'date', 'image_url', 'contacts', 'description',
                      'type', 'active', 'pk']
            found_images, new_images = lost_obj.get_intersected_objects(
                fields=fields,
                seen=True,
                active=True,
            )
            new_image_ids = [found.get('pk') for found in new_images]
            update_lost_and_found(lost_ids=[lost_obj.pk], found_ids=new_image_ids, seen=True)
            image_count, not_active_image_count = update_images_for_context(found_images)
            new_image_count, new_not_active_image_count = update_images_for_context(new_images)
            message = get_message(image_count+new_image_count)
            message = message + f' из них на модерации: {not_active_image_count+new_not_active_image_count}'

        context = {
            "message": message,
            "new_images": new_images,
            "found_images": found_images,
            "lost_points": lost_points,
            "opencage_key": OPENCAGE_KEY,
            "radius": radius,
        }
        return render(request, "world/concrete_search.html", context)


def update_lost_and_found(lost_ids, found_ids, seen: bool = False) -> None:
    lost_found_list = list(
        LostFound(lost_id=lost, found_id=found)
        for found in found_ids for lost in lost_ids
    )
    LostFound.objects.bulk_create(lost_found_list, ignore_conflicts=True)

    if seen:
        seen_datetime = datetime.datetime.now()
        LostFound.objects.filter(
            found_id__in=found_ids, lost_id__in=lost_ids, seen__isnull=True
        ).update(seen=seen_datetime)


@method_decorator(login_required, name='get')
class SendNotifications(TemplateView):
    template_name = 'world/send_notifications.html'

    def post(self, request, *args, **kwargs):
        lost_objects = Image.objects.filter(type=LOST)
        count_notification = 0
        for lost in lost_objects:
            email = lost.email
            old_found_id_set = set(
                LostFound.objects.filter(lost=lost.pk).values_list(FOUND,
                                                                   flat=True))

            found_list = lost.get_intersected_objects(active=True, fields=['pk'])
            found_id_set = set(found['pk'] for found in found_list)
            diff_found_set = found_id_set.difference(old_found_id_set)
            if diff_found_set:
                count_notification += 1
                send_email(
                    subject='Найдены новые вещи',
                    body=f'Найдены вещи соответсвующие <a href="{settings.SITE}/{lost.pk}">вашему объявлению</a>: {len(diff_found_set)}',
                    sender_email=SENDER_EMAIL,
                    receiver_email=email,
                    password=EMAIL_PASSWORD,
                )
                update_lost_and_found(lost_ids=[lost.pk], found_ids=diff_found_set)
        message = f'Уведомления отправлены - {count_notification}'
        context = dict(message=message)
        return render(request, self.template_name, context)


@method_decorator(login_required, name='get')
class Index(TemplateView):
    template_name = 'world/index.html'

    def get(self, request, *args, **kwargs):
        one_day = datetime.timedelta(days=1)
        seven_day = datetime.timedelta(days=7)
        one_month = datetime.timedelta(days=30)
        today = datetime.date.today()
        yesterday = today - one_day
        last_week = today - seven_day
        last_month = today - one_month
        last_day_count = Image.objects.filter(
            date__range=(yesterday, today)).count()
        last_week_count = Image.objects.filter(
            date__range=(last_week, today)).count()
        last_month_count = Image.objects.filter(
            date__range=(last_month, today)).count()
        kwargs.update(
            last_day_count=last_day_count,
            last_week_count=last_week_count,
            last_month_count=last_month_count,
        )
        return super().get(self, request, *args, **kwargs)


@method_decorator(login_required, name='get')
class MyAd(TemplateView):
    template_name = 'world/ad.html'

    def post(self, request, *args, **kwargs):
        uuid = request.POST.get('uuid')
        return redirect(f'/{uuid}', *args, **kwargs)
