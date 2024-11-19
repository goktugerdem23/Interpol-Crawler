import json
import pika
from django.core.management.base import BaseCommand
from interpol_app.models import InterpolData

class Command(BaseCommand):
    help = 'Consume data from RabbitMQ and sync database with Interpol updates'

    def handle(self, *args, **kwargs):
        # RabbitMQ bağlantısı
        connection_parameters = pika.ConnectionParameters('rabbitmq')
        connection = pika.BlockingConnection(connection_parameters)
        channel = connection.channel()
        channel.queue_declare(queue='interpol-data')

        def callback(ch, method, properties, body):
            try:
                data = json.loads(body)

                # Verinin eksik olup olmadığını kontrol et
                required_fields = ["Name", "Age", "Nationality", "img_url"]
                missing_fields = [field for field in required_fields if field not in data]

                if missing_fields:
                    self.stdout.write(self.style.ERROR(f"Missing fields: {', '.join(missing_fields)}"))
                    return  # Eksik veri varsa, işlem yapmadan çık

                # Gelen veriyle mevcut veri arasında karşılaştırma
                existing_record = InterpolData.objects.filter(name=data["Name"]).first()

                if existing_record:
                    # Mevcut kaydı güncelle
                    existing_record.age = data["Age"]
                    existing_record.nationality = data["Nationality"]
                    existing_record.img_url = data["img_url"]
                    existing_record.save()
                    self.stdout.write(self.style.SUCCESS(
                        f"Updated existing record: {data['Name']}"
                    ))
                else:
                    # Yeni bir kayıt ekle
                    InterpolData.objects.create(
                        name=data["Name"],
                        age=data["Age"],
                        nationality=data["Nationality"],
                        img_url=data["img_url"]
                    )
                    self.stdout.write(self.style.SUCCESS(
                        f"Added new record: {data['Name']}"
                    ))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing message: {e}"))

        # RabbitMQ dinleme
        channel.basic_consume(queue='interpol-data', on_message_callback=callback, auto_ack=True)
        self.stdout.write(self.style.NOTICE('Waiting for messages...'))
        channel.start_consuming()

    def check_for_removed_records(self):
        """
        Interpol'un veritabanında artık bulunmayan kayıtları işaretlemek.
        """
        current_names_in_db = set(InterpolData.objects.values_list("name", flat=True))
        names_from_last_sync = self.get_current_interpol_names()

        removed_names = current_names_in_db - names_from_last_sync

        if removed_names:
            self.stdout.write(self.style.WARNING(
                f"Removed records detected: {', '.join(removed_names)}"
            ))
            InterpolData.objects.filter(name__in=removed_names).delete()
            self.stdout.write(self.style.SUCCESS("Removed records have been deleted."))

    def get_current_interpol_names(self):
        """
        RabbitMQ kuyruğundan gelen güncel isimlerin bir listesini döndürür.
        """
        connection_parameters = pika.ConnectionParameters('rabbitmq')
        connection = pika.BlockingConnection(connection_parameters)
        channel = connection.channel()
        channel.queue_declare(queue='interpol-data')
        
        current_names = set()
        
        method_frame, _, body = channel.basic_get(queue='interpol-data', auto_ack=True)
        while method_frame:
            data = json.loads(body)
            if "Name" in data:
                current_names.add(data["Name"])
            method_frame, _, body = channel.basic_get(queue='interpol-data', auto_ack=True)

        connection.close()
        return current_names
