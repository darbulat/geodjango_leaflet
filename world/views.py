import csv
import datetime
import io
import json

from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import Point, MultiPolygon
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from world.helpers import BulkCreateManager
from world.models import Image

RATIO = 1000


def upload_points(request):
    if request.FILES['csv_file']:

        file = request.FILES['csv_file']
        csv_file = file.read().decode('utf-8')
        reader = csv.reader(io.StringIO(csv_file), delimiter=' ', quotechar='|')
        Image.objects.all().delete()
        bulk_mgr = BulkCreateManager(chunk_size=20)
        for id_out, long, lat, date, link, description in reader:
            try:
                date = datetime.date.fromisoformat(date)
                point = Point(x=float(long), y=float(lat))
                bulk_mgr.add(Image(id_out=id_out, point=point,
                                   date=date, link=link,
                                   description=description))

            except ValueError:
                pass

        bulk_mgr.done()
        return render(
            request, 'world/index.html', {'message': 'Данные успешно загружены'}
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
        date__range=[from_date, to_date],
        point__intersects=mp_circles
    ).values()
    images = list([
        {
            'id_out': image['id_out'],
            'x': image['point'].x,
            'y': image['point'].y,
            'date': str(image['date']),
            'link': image['link'],
            'description': image['description'],
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
