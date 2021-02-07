import datetime
import json
import os
import shutil

import fiona
from typing import Dict, List

from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.gis.geos import Polygon
from shapely.geometry import Point, LineString

from djangoProject import settings
from plots import forms
from pyproj import Geod

geoid = Geod(ellps='WGS84')
MIN_DISTANCE = 2


def get_distance(point1, point2) -> float:
    line_string = LineString(
        [Point(point1[1], point1[0]), Point(point2[1], point2[0])]
    )
    return round(geoid.geometry_length(line_string), 3)


def add_distance(lat, long, az, dist) -> list:
    lng_new, lat_new, return_az = geoid.fwd(long, lat, az, dist)
    return [lat_new, lng_new]


def get_area_from_points(points: Dict) -> float:
    lats = []
    longs = []
    for latlong, _ in points.values():
        lats.append(latlong[0])
        longs.append(latlong[1])
    poly_area, _ = geoid.polygon_area_perimeter(longs, lats)
    return round(poly_area / 10000, 4)


def get_polygon_from_points(points: Dict, start_n: str) -> Polygon:
    point = points[start_n][0]
    n = points[start_n][1]
    linear_ring = [point]
    while n != start_n:
        point = points[n][0]
        n = points[n][1]
        linear_ring.append(point)
    linear_ring.append(linear_ring[0])
    return Polygon(linear_ring, srid=4326)


def save_shape_file(polygon):
    schema = {'geometry': 'Polygon',
              'properties': {}}
    geom = {}
    file_path = str(datetime.datetime.now()) + '/polygon.shp'
    file_path = os.path.join(settings.MEDIA_ROOT, file_path)
    os.makedirs(os.path.dirname(file_path))
    crs = {'no_defs': True, 'ellps': 'WGS84',
           'datum': 'WGS84', 'proj': 'longlat'}
    with fiona.open(file_path,
                    'w', driver='ESRI Shapefile',
                    schema=schema, crs=crs) as fi_shp:
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
                fh.read(), content_type="application/vnd.ms-excel"
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
    points: Dict[str: (list, str)] = dict()
    zero_point: Dict[str: (list, str)] = dict()
    zero_lines: Dict[str: List[list]] = dict()
    difference = 0
    polygon_area = 0
    message = ' для скачивания укажите привязки '
    context = dict(line_form=line_form,
                   point_form=point_form,
                   shape_form=shape_form,
                   line_forms=line_forms,
                   points=points,
                   zero_point=zero_point,
                   zero_lines=zero_lines,
                   difference=difference,
                   polygon_area=polygon_area,
                   message=message)

    if request.method == 'POST':
        if request.POST.get('polygon_area'):
            polygon_area = request.POST.get('polygon_area')
        if request.POST.get('difference'):
            difference = request.POST.get('difference')
        if request.POST.get('zero_lines'):
            zero_lines = json.loads(request.POST.get('zero_lines'))
        if request.POST.get('zero_point'):
            zero_point = json.loads(request.POST.get('zero_point'))
        if request.POST.get('points'):
            points = json.loads(request.POST.get('points'))
        if request.POST.get('line_forms'):
            line_forms = json.loads(request.POST.get('line_forms'))
        if shape_form.is_valid():
            points = shape_form.cleaned_data['linear_ring']
            points = json.loads(points)
            if len(points) > 2:
                polygon = get_polygon_from_points(points, '1')
                file_path = save_shape_file(polygon)
                zipfile_path = archive_shape_file(file_path)
                return get_file_response(zipfile_path)
        if point_form.is_valid():
            num = point_form.cleaned_data['num']
            long = point_form.cleaned_data['long']
            lat = point_form.cleaned_data['lat']
            zero_point = {num: [lat, long]}
        if line_form.is_valid():
            start_point_id = line_form.cleaned_data['start_point']
            end_point_id = line_form.cleaned_data['end_point']
            rhumb = line_form.cleaned_data['rhumb']
            distance = line_form.cleaned_data['distance']
            start_points = list(points.keys()) + list(zero_point.keys())
            if start_point_id not in start_points:
                message = f' выберите начальную точку из {start_points}'
            else:
                if start_point_id in zero_point:
                    start_point = zero_point[start_point_id]
                    end_point = add_distance(*start_point, rhumb, distance)
                    zero_lines.update(
                        {start_point_id: [start_point, end_point]}
                    )
                elif end_point_id in points:
                    start_point = points[start_point_id][0]
                    end_point = add_distance(*start_point, rhumb, distance)
                    zero_end_point = points[end_point_id][0]
                    difference = get_distance(zero_end_point, end_point)
                    if difference > MIN_DISTANCE:
                        message = f' расхождение более {MIN_DISTANCE} метров '
                        context.update(points=points, line_forms=line_forms,
                                       line_form=forms.LineForm(),
                                       zero_point=zero_point,
                                       zero_lines=zero_lines,
                                       difference=difference,
                                       polygon_area=polygon_area,
                                       message=message)
                        return render(
                            request, 'plots/index.html', context=context)
                    message = ''
                    end_point = zero_end_point
                else:
                    start_point = points[start_point_id][0]
                    end_point = add_distance(*start_point, rhumb, distance)
                line_forms.append(
                    [start_point_id, end_point_id, rhumb, distance])
                points.update({end_point_id: [end_point, start_point_id]})
                polygon_area = get_area_from_points(points)

        context.update(points=points, line_forms=line_forms,
                       line_form=forms.LineForm(), zero_point=zero_point,
                       zero_lines=zero_lines, difference=difference,
                       polygon_area=polygon_area, message=message)
    return render(request, 'plots/index.html', context=context)
