import csv
import datetime
import io
import json

from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import Point, MultiPoint
from django.contrib.gis.measure import D
from django.db.transaction import atomic
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.views import View
from django.views.generic import UpdateView, DeleteView, TemplateView

from djangoProject.settings import (
    EMAIL_PASSWORD,
    RECEIVER_EMAIL,
    SENDER_EMAIL,
    OPENCAGE_KEY,
    IS_SEND_EMAIL,
)
from world.forms import FoundObjectForm, LostObjectForm
from world.helpers import BulkCreateManager, parse_date_from_str, \
    get_declension, get_found_objects
from world.models import Image, FOUND, LOST
from world.notifications import send_email


@login_required(login_url="/admin")
@atomic
def upload_points(request):
    if file := request.FILES.get("csv_file"):

        csv_file = file.read().decode("utf-8")
        reader = csv.reader(io.StringIO(csv_file), delimiter=";", quotechar="|")
        bulk_mgr = BulkCreateManager(chunk_size=20)
        counter_of_new_objects = 0
        _, rows_count_dict = Image.objects.filter(id_out__isnull=False).delete()
        rows_count = rows_count_dict.get("world.Image") or 0
        try:
            for id_out, lat, long, date, link, description, contacts in reader:
                try:
                    year, month, day = parse_date_from_str(date)
                    date = datetime.date(year=year, month=month, day=day)
                    point = Point(x=float(long), y=float(lat))
                    bulk_mgr.add(
                        Image(
                            id_out=id_out,
                            point=point,
                            date=date,
                            link=link,
                            description=description,
                            contacts=contacts,
                        )
                    )
                    counter_of_new_objects += 1
                except ValueError:
                    pass
        except ValueError:
            pass
        bulk_mgr.done()

        change_counter = counter_of_new_objects - rows_count
        return render(
            request,
            "world/upload.html",
            {
                "message": f"Новых записей: {change_counter}\n"
                           f"Записей в базе: {counter_of_new_objects}"
            },
        )


def get_message(n: int):
    if n == 1:
        return f'Найден {n} {get_declension(n, "объект")}'
    return f'Найдено {n} {get_declension(n, "объект")}'


@login_required(login_url="/admin")
def get_points(request):
    if from_date_str := request.POST.get("from_date"):
        from_date = datetime.date.fromisoformat(from_date_str)
    else:
        from_date = datetime.date.today() - datetime.timedelta(days=2)
    if to_date_str := request.POST.get("to_date"):
        to_date = datetime.date.fromisoformat(to_date_str)
    else:
        to_date = datetime.date.today() + datetime.timedelta(days=1)
    if radius := request.POST.get("radius"):
        radius = float(radius)
    else:
        radius = 50
    obj_type = LOST if request.POST.get("is-lost") else FOUND
    points_list = []
    multi_points = MultiPoint(Point(55.752071, 48.744513))
    if request.POST.get("points"):
        points_list = json.loads(request.POST.get("points"))
        multi_points = MultiPoint(
            *[Point(x=long, y=lat) for long, lat in points_list], srid=4326
        )
    images = Image.objects.filter(
        point__distance_lte=(multi_points, D(m=radius)),
        date__range=[from_date, to_date],
        type=obj_type
    ).values()
    images = list(
        [
            {
                "id": str(image["id"]),
                "x": image["point"][0].x,
                "y": image["point"][0].y,
                "date": str(image["date"]),
                "link": image["link"],
                "type": image["type"],
                "active": str(image["active"]),
                "description": image.get("description", ""),
                "contacts": image["contacts"],
            }
            for image in images
        ]
    )
    message = get_message(len(images))
    context = {
        "images": images,
        "from_date": from_date_str,
        "to_date": to_date_str,
        "radius": float(radius),
        "points": points_list,
        "message": message,
        "opencage_key": OPENCAGE_KEY,
    }
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

            obj.save()
            obj.link = (".." + obj.image_file.url)
            obj.save()

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
            )
        else:
            return HttpResponseBadRequest(
                "Ошибка при отправке сообщения. Повторите попытку позже"
            )

    else:
        form = FoundObjectForm()
        return render(request, "world/send.html", {"form": form})


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

            obj = Image(
                contacts=contacts,
                description=description,
                point=multi_point,
                image_file=file,
                date=date,
                email=email,
                type=obj_type,
                radius=radius
            )

            obj.save()
            obj.link = (".." + obj.image_file.url)
            obj.save()

            send_email(
                subject='Ваше объявление скоро будет добавлено',
                body=f'Ссылка на личный кабинет: <a href="loforoll.com/{obj.id}">{obj.id}</a>',
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
                content=f"Ваше сообщение отправлено на модерацию\n"
                        f"<a href='/{obj.id}'>ссылка</a> для вашего объявления"
            )
        else:
            return HttpResponseBadRequest(
                "Ошибка при отправке сообщения. Повторите попытку позже"
            )

    else:
        form = LostObjectForm()
        return render(request, "world/send.html", {"form": form})


@login_required(login_url="/admin")
def upload(request):
    if request.method == "GET":
        return render(request, "world/upload.html", {})
    if request.method == "POST":
        return upload_points(request)


@login_required(login_url="/admin")
def search(request):
    if request.method == "GET":
        return render(
            request, "world/search.html",
            dict(opencage_key=OPENCAGE_KEY, images=[])
        )
    if request.method == "POST":
        return get_points(request)


@login_required(login_url="/admin")
def index(request):
    return render(
        request, "world/index.html",
        dict(opencage_key=OPENCAGE_KEY, images=[])
    )


@login_required(login_url="/admin")
def detail_object(request):
    return render(request, "world/image_form.html", dict())


class ImageUpdate(UpdateView):

    model = Image
    fields = ['date', 'contacts', 'email', 'radius', 'description']


class ImageDelete(DeleteView):

    model = Image


class ImageIntersect(View):

    def get(self, request, *args, **kwargs):
        message = "Здесь будут найденные вещи, которые вы могли потерять"
        image_id = kwargs.get('pk')
        lost_obj = Image.objects.get(pk=image_id)
        radius = lost_obj.radius
        lost_points = list(dict(x=point.x, y=point.y) for point in lost_obj.point)
        found_images = get_found_objects(
            lost_date=lost_obj.date,
            multi_point=lost_obj.point,
            radius=radius
        )

        for image in found_images:
            image.update(
                x=image.get('point')[0].x,
                y=image.get('point')[0].y,
                date=str(image.get('date')),
                active=str(image.get('active'))
            )
            del image['point']
        if found_images:
            message = get_message(len(found_images))
        context = {
            "message": message,
            "found_images": found_images,
            "lost_points": lost_points,
            "opencage_key": OPENCAGE_KEY,
            "radius": radius,
        }
        return render(request, "world/concrete_search.html", context)
