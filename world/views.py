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
from django.views.decorators.csrf import csrf_exempt

from djangoProject.settings import (EMAIL_PASSWORD, RECEIVER_EMAIL,
                                    SENDER_EMAIL, OPENCAGE_KEY)
from world.forms import FoundObjectForm
from world.helpers import BulkCreateManager, parse_date_from_str, get_declension
from world.models import Image
from world.notifications import send_email


@atomic
def upload_points(request):
    if request.FILES['csv_file']:

        file = request.FILES['csv_file']
        csv_file = file.read().decode('utf-8')
        reader = csv.reader(
            io.StringIO(csv_file),
            delimiter=';', quotechar='|'
        )
        bulk_mgr = BulkCreateManager(chunk_size=20)
        counter_of_new_objects = 0
        _, rows_count_dict = Image.objects.filter(id_out__isnull=False).delete()
        rows_count = rows_count_dict.get('world.Image') or 0
        try:
            for id_out, lat, long, date, link, description, contacts in reader:
                try:
                    year, month, day = parse_date_from_str(date)
                    date = datetime.date(year=year, month=month, day=day)
                    point = Point(x=float(long), y=float(lat))
                    bulk_mgr.add(Image(id_out=id_out, point=point,
                                       date=date, link=link,
                                       description=description,
                                       contacts=contacts))
                    counter_of_new_objects += 1
                except ValueError:
                    pass
        except ValueError:
            pass
        bulk_mgr.done()

        change_counter = counter_of_new_objects - rows_count
        return render(
            request, 'world/index.html',
            {'message': f'Новых записей: {change_counter}\n'
                        f'Записей в базе: {counter_of_new_objects}'}
        )


def get_message(n: int):
    if n == 1:
        return f'Найден {n} {get_declension(n, "объект")}'
    return f'Найдено {n} {get_declension(n, "объект")}'


def get_points(request):
    if from_date_str := request.POST.get('from_date'):
        from_date = datetime.date.fromisoformat(from_date_str)
    else:
        from_date = datetime.date.today() - datetime.timedelta(days=2)
    if to_date_str := request.POST.get('to_date'):
        to_date = datetime.date.fromisoformat(to_date_str)
    else:
        to_date = datetime.date.today() + datetime.timedelta(days=1)
    if radius := request.POST.get('radius'):
        radius = float(radius)
    else:
        radius = 30
    points_list = []
    multi_points = MultiPoint(Point(55.752071, 48.744513))
    if request.POST.get('points'):
        points_list = json.loads(request.POST.get('points'))
        multi_points = MultiPoint(*[
            Point(x=long, y=lat) for long, lat in points_list
        ], srid=4326)
    images = Image.objects.filter(
        point__distance_lte=(multi_points, D(m=radius)),
        date__range=[from_date, to_date],
    ).values()
    images = list([
        {
            'id_out': image['id_out'],
            'x': image['point'].x,
            'y': image['point'].y,
            'date': str(image['date']),
            'link': image['link'],
            'description': image['description']
            if image['description'] is not None else '',
            'contacts': image['contacts']
        } for image in images
    ])
    message = get_message(len(images))
    context = {
        "images": images,
        'from_date': from_date_str,
        'to_date': to_date_str,
        'radius': float(radius),
        'points': points_list,
        'message': message,
        'opencage_key': OPENCAGE_KEY,
    }
    return render(request, 'world/main.html', context)


def send_object(request):
    if request.method == 'POST':

        form = FoundObjectForm(request.POST, request.FILES)
        if form.is_valid():
            description = form.cleaned_data['description']
            contacts = form.cleaned_data['contacts']
            body = f'Описание: {description} <br> Контакты: {contacts} <br>'
            point: Point = form.cleaned_data['point']
            if point:
                point.transform(4326)
                location = dict(x=point.x, y=point.y)
                body += f'Координаты: {location}'

            file = form.files.get('image_file')
            send_email(subject='Найден новый объект',
                       body=body, fp=file,
                       sender_email=SENDER_EMAIL,
                       receiver_email=RECEIVER_EMAIL,
                       password=EMAIL_PASSWORD)
            return HttpResponse(
                content='Ваше сообщение отправлено администраторам, '
                        'спасибо за бдительность!'
            )
        else:
            return HttpResponseBadRequest(
                'Ошибка при отправке сообщения. Повторите попытку позже')

    else:
        form = FoundObjectForm()
        return render(request, 'world/send.html', {'form': form})


def get_location(request, id_out):
    if request.method == 'GET':
        return render(
            request, 'world/location.html',
            dict(opencage_key=OPENCAGE_KEY, id_out=id_out)
        )
    if request.method == 'POST':
        if request.POST.get('point'):
            point = json.loads(request.POST.get('point'))
            body = f'ID объекта: {id_out}<br>X = {point[0]}  Y = {point[1]}'
            send_email(subject='Получены новые координаты', body=body,
                       sender_email=SENDER_EMAIL, receiver_email=RECEIVER_EMAIL,
                       password=EMAIL_PASSWORD)
            return HttpResponse(content='Координаты отправлены администратору, '
                                        'спасибо за бдительность!')
        return render(request, 'world/location.html',
                      dict(opencage_key=OPENCAGE_KEY, id_out=id_out))


@login_required(login_url='/admin')
def index(request):
    if request.method == 'GET':
        return render(request, 'world/index.html', {})
    if request.method == 'POST':
        return upload_points(request)


@csrf_exempt
def main(request):
    if request.method == 'GET':
        return render(request, 'world/main.html',
                      dict(opencage_key=OPENCAGE_KEY, images=[]))
    if request.method == 'POST':
        return get_points(request)
