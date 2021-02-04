import datetime
import json
import os
import shutil

import fiona
from typing import Dict

from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.gis.geos import Polygon

from djangoProject import settings
from plots import forms
from pyproj import Geod

geoid = Geod(ellps='WGS84')


def add_distance(lat, long, az, dist):
    lng_new, lat_new, return_az = geoid.fwd(long, lat, az, dist)
    return lat_new, lng_new


def get_polygon_from_points(points: Dict, start_n: str) -> Polygon:
    point = points[start_n][0]
    n = points[start_n][1]
    linear_ring = [point]
    while n != start_n:
        point = points[n][0]
        n = points[n][1]
        linear_ring.append(point)
    linear_ring.append(linear_ring[0])
    return Polygon(linear_ring)


def save_shape_file(polygon):
    schema = {'geometry': 'Polygon',
              'properties': {}}
    geom = {}
    file_path = str(datetime.datetime.now()) + '/polygon.shp'
    file_path = os.path.join(settings.MEDIA_ROOT, file_path)
    os.makedirs(os.path.dirname(file_path))
    with fiona.open(file_path,
                    'w', driver='ESRI Shapefile',
                    schema=schema) as fi_shp:
        geom['geometry'] = json.loads(polygon.geojson)
        fi_shp.write(geom)
    return file_path


def archive_shape_file(path):
    zipfile_path = os.path.dirname(path)

    shutil.make_archive(zipfile_path, "zip", zipfile_path)
    return zipfile_path + '.zip'


def get_file_response(path):
    if os.path.exists(path):
        with open(path, 'rb') as fh:
            response = HttpResponse(
                fh.read(), content_type="application/zip"
            )
            response[
                'Content-Disposition'] = 'inline; filename=' + os.path.basename(
                path)
            return response


def index(request):
    line_forms = []
    line_form = forms.LineForm(request.POST)
    point_form = forms.PointForm(request.POST)
    shape_form = forms.ShapeForm(request.POST)
    points: Dict[str: (tuple, str)] = dict()

    context = dict(line_form=line_form,
                   point_form=point_form,
                   shape_form=shape_form,
                   line_forms=line_forms,
                   points=points)

    if request.method == 'POST':
        if request.POST.get('points'):
            points = json.loads(request.POST.get('points'))
            point_form.fields['lat'].initial = points['0'][0][0]
            point_form.fields['long'].value = points['0'][0][1]
        if shape_form.is_valid():
            points = shape_form.cleaned_data['linear_ring']
            points = json.loads(points)
            if len(points) > 2:
                polygon = get_polygon_from_points(points, '1')
                file_path = save_shape_file(polygon)
                zipfile_path = archive_shape_file(file_path)
                return get_file_response(zipfile_path)

        if request.POST.get('line_forms'):
            line_forms = json.loads(request.POST.get('line_forms'))
        if point_form.is_valid():
            num = point_form.cleaned_data['num']
            long = point_form.cleaned_data['long']
            lat = point_form.cleaned_data['lat']
            point = [lat, long]
            points.update({num: [point, -1]})
        if line_form.is_valid():
            start_point_id = line_form.cleaned_data['start_point']
            end_point_id = line_form.cleaned_data['end_point']
            rhumb = line_form.cleaned_data['rhumb']
            distance = line_form.cleaned_data['distance']
            start_point = points[start_point_id][0]
            lat, long = add_distance(*start_point, rhumb, distance)
            points.update({end_point_id: [[lat, long], start_point_id]})
            line_forms.append([start_point_id, end_point_id, rhumb, distance])
            context.update(points=points, line_forms=line_forms,
                           line_form=forms.LineForm())
    return render(request, 'plots/index.html', context=context)
