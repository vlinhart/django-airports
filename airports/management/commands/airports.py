# -*- coding: utf-8 -*-

import codecs
import csv
import itertools
import logging
import os

import requests
from cities.models import Country, City
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db.models import Q
from tqdm import tqdm

from airports.models import Airport

ENDPOINT_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat"

"""
Maximum distance used to filter out too distant cities.
"""
MAX_DISTANCE_KM = 200

APP_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..'))

logger = logging.getLogger("airports")


def get_airport(longitude, latitude, name, iata, icao, altitude, city, country):
    """

    :param longitude:
    :param latitude:
    :param name:
    :param iata:
    :param icao:
    :param altitude:
    :param city:
    :param country:
    :return:
    """
    point = Point(longitude, latitude, srid=4326)

    name = name or city.name

    if icao == r'\N':
        icao = ''
    try:
        altitude = round(altitude * 0.3048, 2)
    except Exception:
        altitude = 0.0

    airport, created = Airport.objects.get_or_create(
        iata=iata, icao=icao, name=name, altitude=altitude, location=point, country=country, city=city,
    )
    if created:
        logger.debug("Added airport: %s", airport)
    return airport


def get_country(name, city):
    """

    :param name:
    :param city:
    :return:
    """

    qs_all = Country.objects.all()

    qs = qs_all.filter(name__iexact=name)  # first attempt
    if qs.count() == 1:
        return qs.first()

    qs = qs_all.filter(alt_names__name__iexact=name)  # second attempt
    if qs.count() == 1:
        return qs.first()

    if city is not None:
        qs = qs_all.filter(cities=city)
        if qs.count() >= 1:
            return qs.first()  # third attempt

    return None


def get_city(name, latitude, longitude):
    """

    :param name:
    :param latitude:
    :param longitude:
    :return: None if something wrong.
    """

    point = Point(latitude, longitude, srid=4326)

    qs_all = City.objects.all()

    qs = qs_all.filter(name_std__iexact=name)
    if qs.count() == 1:
        return qs.first()

    qs = qs_all.filter(Q(name__iexact=name) | Q(alt_names__name__iexact=name))
    if qs.count() == 1:
        return qs.first()

    qs = qs_all.all() \
        .annotate(distance=Distance('location', point)) \
        .filter(distance__lte=MAX_DISTANCE_KM * 1000) \
        .order_by('distance').all()

    if qs.count() >= 1:
        return qs.first()
    else:
        return None


def get_lines(download_url):
    # Streaming, so we can iterate over the response.
    req = requests.get(download_url, stream=True)
    lines = codecs.iterdecode(req.iter_lines(), encoding='utf-8')
    return lines


def read_airports(reader):
    for row in reader:
        # print(row)
        latitude = float(row['latitude'])
        longitude = float(row['longitude'])
        city_name = row['city_name']
        country_name = row['country_name']

        name = row['name'].strip()
        iata = row['iata'].strip()
        icao = row['icao'].strip()

        altitude = int(row['altitude'].strip())

        if Airport.objects.filter(iata=iata).all().count() == 0:
            city = get_city(city_name, latitude=latitude, longitude=longitude)
            if city is None:
                logger.warning(
                    'Airport: {name}: Cannot find city: {city_name}.'.format(name=name, city_name=city_name))

            country = get_country(country_name, city)
            if country is None:
                logger.warning(
                    'Airport:  {name}: Cannot find country: {country_name}'.format(name=name,
                                                                                   country_name=country_name))

            airport = get_airport(longitude, latitude, name, iata, icao, altitude, city, country)
            yield airport


class Command(BaseCommand):
    default_format = 'airport_id,name,city_name,country_name,iata,icao,latitude,longitude,altitude,timezone,dst'

    help = """Imports airport data from CSV into DB, complementing it with country/city information"""

    def handle(self, *args, **options):
        logger.info('Checking countries and cities')
        if City.objects.all().count() == 0 or Country.objects.all().count() == 0:
            call_command('cities', '--import', 'country,city')

        columns = self.default_format.split(',')

        lines = get_lines(ENDPOINT_URL)

        reader = csv.DictReader(lines, dialect='excel', fieldnames=columns)

        # skipping firstline: is the header I'm overwriting
        for data in tqdm(read_airports(reader),
                         desc="Importing Airports"
                         ):
            pass
