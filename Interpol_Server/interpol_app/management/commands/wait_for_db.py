import time
from django.db import connections
from django.db.utils import OperationalError
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    """Django komutu: veritabanı bağlantısına kadar bekler"""

    def handle(self, *args, **options):
        self.stdout.write('Veritabanı bağlantısı bekleniyor...')
        db_conn = None
        while not db_conn:
            try:
                db_conn = connections['default']
            except OperationalError:
                self.stdout.write('Veritabanı hazır değil, 1 saniye sonra tekrar denenecek...')
                time.sleep(20)

        self.stdout.write(self.style.SUCCESS('Veritabanı bağlantısı başarılı!'))
