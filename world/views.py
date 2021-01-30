import csv
import datetime
import io
import json

from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import Point, MultiPolygon
from django.db.transaction import atomic
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from world.forms import FoundObjectForm
from world.helpers import BulkCreateManager, parse_date_from_str
from world.models import Image

RATIO = 50000


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
        for id_out, lat, long, date, link, description in reader:
            try:
                year, month, day = parse_date_from_str(date)
                date = datetime.date(year=year, month=month, day=day)
                point = Point(x=float(long), y=float(lat))
                bulk_mgr.add(Image(id_out=id_out, point=point,
                                   date=date, link=link,
                                   description=description))
                counter_of_new_objects += 1
            except ValueError:
                pass
        bulk_mgr.done()

        change_counter = counter_of_new_objects - rows_count
        return render(
            request, 'world/index.html',
            {'message': f'Новых записей: {change_counter}\n'
                        f'Записей в базе: {counter_of_new_objects}'}
        )


def get_declension(number, word):
    declensions_dict = {
        'объект': ['объект', 'объекта', 'объектов'],
    }
    if number // 10 == 1:
        return declensions_dict[word][2]
    last_number = number % 10
    if last_number == 1:
        return declensions_dict[word][0]
    if 2 <= last_number <= 4:
        return declensions_dict[word][1]
    return declensions_dict[word][2]


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
        radius = int(radius) / RATIO
    else:
        radius = 100 / RATIO
    points_list = []
    if request.POST.get('points'):
        points_list = json.loads(request.POST.get('points'))
        circles = [
            Point(x=long, y=lat).buffer(radius)
            for long, lat in points_list
        ]
        mp_circles = MultiPolygon(circles)
    else:
        mp_circles = Point(x=0, y=0)
    images = Image.objects.filter(
        point__intersects=mp_circles,
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
        } for image in images
    ])
    message = get_message(len(images))
    context = {
        "images": images,
        'from_date': from_date_str,
        'to_date': to_date_str,
        'radius': int(radius * RATIO),
        'points': points_list,
        'message': message,
    }
    return render(request, 'world/main.html', context)


def send_object(request):

    if request.method == 'POST':

        form = FoundObjectForm(request.POST, request.FILES)
        if form.is_valid():
            return HttpResponse(
                content='Спасибо! Ваше сообщение отправлено.<br>'
                        'Вам придет сообщение с просьбой указать местоположение найденной вещи')
        else:
            return HttpResponseBadRequest(
                'Ошибка при отправке сообщения. Попробуйте повторить попытку позже')

    else:
        form = FoundObjectForm()
        return render(request, 'world/send.html', {'form': form})


@login_required(login_url='/admin')
def index(request):
    if request.method == 'GET':
        return render(request, 'world/index.html', {})
    if request.method == 'POST':
        return upload_points(request)


@csrf_exempt
def main(request):
    if request.method == 'GET':
        return render(request, 'world/main.html', dict(images=[]))
    if request.method == 'POST':
        return get_points(request)
