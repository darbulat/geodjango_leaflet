import csv
import datetime
import io
import json

from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import Point, MultiPolygon
from django.http import HttpResponse
from django.shortcuts import render
from django.template import loader
from django.views.decorators.csrf import csrf_exempt

from world.models import Image


def upload_points(request):
    if request.method == 'POST' and request.FILES['csv_file']:
        file = request.FILES['csv_file']
        csv_file = file.read().decode('utf-8')
        reader = csv.reader(io.StringIO(csv_file), delimiter=' ', quotechar='|')
        for id_out, long, lat, date, link in reader:
            try:
                date = datetime.date.fromisoformat(date)
                point = Point(x=float(long), y=float(lat))
                image = Image(id_out=id_out, point=point, date=date, link=link)
                image.save()
            except ValueError:
                pass

    return HttpResponse(True)


def get_points(request):
    from_date = datetime.date.fromisoformat(request.POST.get('from_date'))
    to_date = datetime.date.fromisoformat(request.POST.get('to_date'))
    radius = int(request.POST.get('radius')) / 1000
    points_list = json.loads(request.POST.get('points'))
    circles = [
        Point(x=long, y=lat).buffer(radius)
        for long, lat in points_list
    ]
    mp_circles = MultiPolygon(circles)
    images = Image.objects.filter(
        date__range=[from_date, to_date],
        point__intersects=mp_circles
    ).values('date', 'link', 'point', 'id_out')
    images = list([
        {
            'id_out': image['id_out'],
            'x': image['point'].x,
            'y': image['point'].y,
            'date': str(image['date']),
            'link': image['link']
        } for image in images
    ])
    context = {"images": images}
    return render(request, 'world/main.html', context)


@login_required(login_url='/admin')
def index(request):
    template = loader.get_template('world/index.html')
    return HttpResponse(template.render({}, request))


@csrf_exempt
def main(request):
    if request.method == 'GET':
        return render(request, 'world/main.html', {})
    if request.method == 'POST':
        return get_points(request)
