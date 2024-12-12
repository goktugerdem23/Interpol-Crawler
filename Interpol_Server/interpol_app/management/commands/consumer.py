import json
import pika
from django.core.management.base import BaseCommand
from interpol_app.models import InterpolData
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Consume data from RabbitMQ and sync database with Interpol updates'

    def handle(self, *args, **kwargs):
        connection_parameters = pika.ConnectionParameters('rabbitmq')

        with pika.BlockingConnection(connection_parameters) as connection:
            channel = connection.channel()

            # Declare queue if not exists
            channel.queue_declare(queue='interpol-data')

            # Callback for consuming messages
            def callback(ch, method, properties, body):
                try:
                    data = json.loads(body)
                    self.process_message(data)
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    self.stdout.write(self.style.ERROR(f"Error processing message: {e}"))

            # Start consuming
            self.stdout.write(self.style.NOTICE('Listening...'))
            channel.basic_consume(queue='interpol-data', on_message_callback=callback)
            channel.start_consuming()

    def process_message(self, data):
        existing_record = InterpolData.objects.filter(
            family_name=data["family_name"], forename=data["forename"]
        ).first()

        if existing_record:
            existing_record.age = data["age"]
            existing_record.nationality = data["nationality"]
            existing_record.img_url = data["img_url"]
            existing_record.save()

            self.stdout.write(self.style.SUCCESS(
                f"Updated existing record: {data['family_name']} {data['forename']}"
            ))
        else:
            InterpolData.objects.create(
                family_name=data["family_name"],
                forename=data["forename"],
                age=data["age"],
                nationality=data["nationality"],
                img_url=data["img_url"]
            )
            self.stdout.write(self.style.SUCCESS(
                f"Added new record: {data['family_name']} {data['forename']}"
            ))

    def check_for_removed_records(self):
        current_records_in_db = self.get_current_interpol_records()

        records_from_last_sycn = self.fetch_rabbitmq_records()
        removed_records = current_records_in_db - records_from_last_sycn

        if removed_records:
            self.stdout.write(self.style.WARNING(
                f"Removed record detected: {', '.join([f''])}"
            ))
        else:
            self.stdout.write(self.style.SUCCESS("No removed records detected"))
      

    def get_current_interpol_records(self):
        return set(
            InterpolData.objects.values_list("family_name","forename")
        )
    


    def fetch_rabbitmq_records(self):
        connection_parameters = pika.ConnectionParameters('rabbitmq')
        current_records = set()

        with pika.BlockingConnection(connection_parameters) as connection:
            channel = connection.channel()
            channel.queue_declare(queue='interpol-data')

            while True:
                method_frame, _, body = channel.basic_get(queue='interpol-data', auto_ack=True)
                if not method_frame:
                    break

                try:
                    data = json.loads(body)
                    if "family_name" in data and "forename" in data:
                        current_records.add((data["family_name"], data["forename"]))
                except json.JSONDecodeError:
                    self.stdout.write(self.style.ERROR("Failed to decode RabbitMQ message as JSON"))

        return current_records

        

   

    
