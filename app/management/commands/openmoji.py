import io
import zipfile

import requests
from django.core.management.base import BaseCommand

NAME = "openmoji-72x72-color.zip"


class Command(BaseCommand):
    help = "Fetch OpenMoji PNGs from download."
    url = f"https://github.com/hfg-gmuend/openmoji/releases/latest/download/{NAME}"

    def get(self):
        print(f"Downloading {NAME}")
        r = requests.get(self.url, stream=True)
        c = io.BytesIO(r.content)
        with zipfile.ZipFile(c) as zip_file:
            zip_file.extractall("static/openmoji")


    def handle(self, *args, **options):
        self.get()
