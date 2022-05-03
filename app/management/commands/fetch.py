from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import feedparser
import requests
from dateutil.parser import parse
from django.core.management.base import BaseCommand

from app.filters import hostname
from app.models import Article
from app.parsers import dehtmlize, fetch_content, get_url
from project.vars import FEEDS


class Command(BaseCommand):
    help = "Fetch articles from feeds."
    cores = 4
    hours = 48 * 3600
    ignored = [
        "https://kottke.org/quick-links"
    ]
    errors = []

    @property
    def now(self):
        return datetime.now(timezone.utc).timestamp()

    def get_entries(self, feed):
        r = requests.get(feed)
        print(feed)
        entries = feedparser.parse(r.text).entries
        for entry in entries:
            try:
                origlink = entry.get('feedburner_origlink')
                entry.link = origlink if origlink else entry.link
                url = get_url(entry.link)
                published = parse(entry.published).astimezone(timezone.utc).timestamp()
                if self.now > published > self.now - self.hours and url not in self.ignored:
                    article, is_created = Article.objects.get_or_create(
                        url=url,
                        title=dehtmlize(entry.title),
                        domain=hostname(url),
                        pub_at=published,
                        author=getattr(entry, 'author', '')
                    )
            except Exception as e:
                self.errors.append("{0} {1}".format(entry.link, e))

    def grab_entries(self):
        with ThreadPoolExecutor(max_workers=self.cores) as executor:
            executor.map(self.get_entries, FEEDS)

    def cleanup(self):
        q = Article.objects.filter(pub_at__lt=self.now - self.hours)
        c = q.count()
        q.delete()
        print("Deleted {0} entries".format(c))

    def get_content(self, article):
        description, paragraphs = fetch_content(article.url)
        article.description = description
        article.paragraphs = paragraphs
        article.save(update_fields=['description', 'paragraphs'])
        print(article.url, len(paragraphs))
        print(article.description)

    def grab_content(self):
        articles = Article.objects.filter(description='').order_by('-id')
        with ThreadPoolExecutor(max_workers=self.cores) as executor:
            executor.map(self.get_content, articles)

    def handle(self, *args, **options):
        self.grab_entries()
        self.cleanup()
        self.grab_content()
        for e in self.errors:
            print(e)
