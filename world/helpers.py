import datetime
from collections import defaultdict
from typing import Tuple, List, Dict

from django.apps import apps
from django.contrib.gis.geos import MultiPoint
from django.contrib.gis.measure import D
from django.db.models.sql import Query

from world.models import Image, FOUND


class BulkCreateManager(object):
    """
    This helper class keeps track of ORM objects to be created for multiple
    model classes, and automatically creates those objects with `bulk_create`
    when the number of objects accumulated for a given model class exceeds
    `chunk_size`.
    Upon completion of the loop that's `add()`ing objects, the developer must
    call `done()` to ensure the final set of objects is created for all models.
    """

    def __init__(self, chunk_size=100):
        self._create_queues = defaultdict(list)
        self.chunk_size = chunk_size

    def _commit(self, model_class):
        model_key = model_class._meta.label
        model_class.objects.bulk_create(self._create_queues[model_key])
        self._create_queues[model_key] = []

    def add(self, obj):
        """
        Add an object to the queue to be created, and call bulk_create if we
        have enough objs.
        """
        model_class = type(obj)
        model_key = model_class._meta.label
        self._create_queues[model_key].append(obj)
        if len(self._create_queues[model_key]) >= self.chunk_size:
            self._commit(model_class)

    def done(self):
        """
        Always call this upon completion to make sure the final partial chunk
        is saved.
        """
        for model_name, objs in self._create_queues.items():
            if len(objs) > 0:
                self._commit(apps.get_model(model_name))


def parse_date_from_str(date_str: str) -> Tuple:
    if '.' in date_str:
        day, month, year = date_str.split('.')
    elif '-' in date_str:
        year, month, day = date_str.split('-')
    else:
        raise ValueError('Wrong date format')
    return tuple(map(int, [year, month, day]))


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


def get_found_objects(lost_date: datetime.date,
                      multi_point: MultiPoint,
                      radius: float,
                      fields: list,
                      active: bool = None) -> List[Dict]:
    query = dict(
        point__distance_lte=(multi_point, D(m=radius)),
        date__gte=lost_date,
        type=FOUND
    )
    if active is not None:
        query.update(active=active)
    images = Image.objects.filter(**query).values(*fields)
    return list(images)


def get_message(n: int):
    if n == 1:
        return f'Найден {n} {get_declension(n, "объект")}'
    return f'Найдено {n} {get_declension(n, "объект")}'


def update_images_for_context(images: List) -> Tuple:
    not_active_image_count = 0

    for image in images:
        if not image.get('active'):
            not_active_image_count += 1
        image.update(
            x=image.get('point')[0].x,
            y=image.get('point')[0].y,
            date=str(image.get('date')),
            active=str(image.get('active'))
        )
        if not image.get('contacts'):
            image.update(contacts='')
        if 'point' in image:
            del image['point']
        if 'pk' in image:
            del image['pk']

    return len(images), not_active_image_count
