import csv
import io
import json
import sys
import zipfile
from collections import defaultdict

import requests
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Fetch users, comments from db.json."
    url = "https://simplemaps.com/static/data/world-cities/basic/simplemaps_worldcities_basicv1.73.zip"

    def get_csv(self):
        r = requests.get(self.url, stream=True)
        c = io.BytesIO(r.content)
        with zipfile.ZipFile(c) as zip:
            with zip.open('worldcities.csv') as file:
                return io.StringIO(file.read().decode())

    def fix_country(self, v):
        replaces = [
            (", The", ""),
            ("Korea, South", "South Korea"),
            ("Korea, North", "North Korea"),
            ("Curaçao", "Curacao"),
            ("Côte D’Ivoire", "Cote d'Ivoire"),
            ("Congo (Brazzaville)", "Congo-Brazzaville"),
            ("Congo (Kinshasa)", "Congo-Kinshasa"),
            ("Micronesia, Federated States Of", "Micronesia"),
            ("Falkland Islands (Islas Malvinas)", "Falkland Islands"),
            (", And Tristan Da Cunha", " and Tristan da Cunha"),
            (" And ", " and "),
            (" The ", " the "),
            (" Of ", " of ")
        ]
        for before, after in replaces:
            v = v.replace(before, after)
        return v

    def fix_city(self, v):
        replaces = [
            ("Beaubassin East / Beaubassin-est", "Beaubassin East"),
            ("Islamorada, Village of Islands", "Islamorada"),
            ("Dolores Hidalgo Cuna de la Independencia Nacional", "Dolores Hidalgo"),
            ("`", "'")
        ]
        for before, after in replaces:
            v = v.replace(before, after)
        return v

    def convert(self):
        world = defaultdict(set)
        maxim, loc = 0, ""
        reader = csv.DictReader(self.get_csv())
        for row in reader:
            country = self.fix_country(row['country'])
            city = self.fix_city(row['city_ascii'])
            world[country].add(city)
            name = f"{city}, {country}"
            if len(name) > maxim:
                maxim, loc = len(name), name

        print('max', maxim)
        print('loc', loc)
        print('size', sys.getsizeof(world))
        print('countries', len(world.keys()))
        print('cities', sum(len(v) for k, v in world.items()))

        for country, cities in world.items():
            world[country] = sorted(cities)

        with open('static/worldcities.json', 'w') as file:
            json.dump(world, file, sort_keys=True, indent=4)

    def handle(self, *args, **options):
        self.convert()
