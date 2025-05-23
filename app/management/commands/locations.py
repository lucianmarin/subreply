import csv
import io
import json
import sys
import zipfile
from collections import defaultdict

import requests
from django.core.management.base import BaseCommand

NAME = "simplemaps_worldcities_basicv1.77.zip"


class Command(BaseCommand):
    help = "Fetch cities, countries from download."
    url = f"https://simplemaps.com/static/data/world-cities/basic/{NAME}"

    def get_csv(self):
        print(f"Downloading {NAME}")
        r = requests.get(self.url, stream=True)
        c = io.BytesIO(r.content)
        with zipfile.ZipFile(c) as zip_file, zip_file.open('worldcities.csv') as file:
            self.csv_file = io.StringIO(file.read().decode())

    def fix_country(self, name):
        replaces = [
            (", The", ""),
            ("Korea, South", "South Korea"),
            ("Korea, North", "North Korea"),
            ("Curaçao", "Curacao"),
            ("Czechia", "Czech Republic"),
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
            name = name.replace(before, after)
        return name

    def fix_city(self, name):
        replaces = [
            ("Beaubassin East / Beaubassin-est", "Beaubassin East"),
            ("Islamorada, Village of Islands", "Islamorada"),
            ("Dolores Hidalgo Cuna de la Independencia Nacional", "Dolores Hidalgo"),
            ("`", "'")
        ]
        for before, after in replaces:
            name = name.replace(before, after)
        return name.split(" / ")[0]

    def convert(self):
        print("Converting CSV file to JSON files")
        cities = defaultdict(set)
        countries = {}
        maxim, location = 0, ""
        reader = csv.DictReader(self.csv_file)
        for row in reader:
            country = self.fix_country(row['country'])
            city = self.fix_city(row['city_ascii'])
            name = f"{city}, {country}"
            if name.count(", ") == 1:
                cities[country].add(city)
                countries[row['iso2']] = country
                if len(name) > maxim:
                    maxim, location = len(name), name

        print('Maxim', maxim, "characters")
        print('Location', location)
        print('Size', sys.getsizeof(self.csv_file))
        print('Countries', len(cities.keys()))
        print('Cities', sum(len(v) for k, v in cities.items()))

        for country, city_set in cities.items():
            cities[country] = sorted(city_set)

        with open('static/cities.json', 'w') as file:
            json.dump(cities, file, sort_keys=True, indent=4)

        with open('static/countries.json', 'w') as file:
            json.dump(countries, file, sort_keys=True, indent=4)

    def handle(self, *args, **options):
        self.get_csv()
        self.convert()
