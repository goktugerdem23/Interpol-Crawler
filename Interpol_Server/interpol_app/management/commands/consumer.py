import json
import pika
from django.core.management.base import BaseCommand
from interpol_app.models import InterpolData

class Command(BaseCommand):
    help = 'Consume data from RabbitMQ and sync database with Interpol updates'

    def handle(self, *args, **kwargs):
        # Establishing connection to the RabbitMQ server
        connection_parameters = pika.ConnectionParameters('rabbitmq')
        connection = pika.BlockingConnection(connection_parameters)
        channel = connection.channel()
        
        # Declare a queue named 'interpol-data' if it doesn't already exist
        channel.queue_declare(queue='interpol-data')

        # Define the callback function to process messages from the queue
        def callback(ch, method, properties, body):
            try:
                # Parse the incoming message as JSON
                data = json.loads(body)

                # Check if a record with the same name already exists in the database
                existing_record = InterpolData.objects.filter(name=data["Name"]).first()

                if existing_record:
                    # If the record exists, update its fields with new data
                    existing_record.age = data["Age"]
                    existing_record.nationality = data["Nationality"]
                    existing_record.img_url = data["img_url"]
                    existing_record.save()

                    # Log a success message for the updated record
                    self.stdout.write(self.style.SUCCESS(
                        f"Updated existing record: {data['Name']}"
                    ))
                else:
                    # If the record doesn't exist, create a new one
                    InterpolData.objects.create(
                        name=data["Name"],
                        age=data["Age"],
                        nationality=data["Nationality"],
                        img_url=data["img_url"]
                    )

                    # Log a success message for the new record
                    self.stdout.write(self.style.SUCCESS(
                        f"Added new record: {data['Name']}"
                    ))

            except Exception as e:
                # Log an error if message processing fails
                self.stdout.write(self.style.ERROR(f"Error processing message: {e}"))

        # Start consuming messages from the queue, calling the callback function for each
        channel.basic_consume(queue='interpol-data', on_message_callback=callback, auto_ack=True)
        
        # Log a message indicating that the script is waiting for messages
        self.stdout.write(self.style.NOTICE('Waiting for messages...'))
        channel.start_consuming()

    def check_for_removed_records(self):
     
        # Get the names of all records currently in the database
        current_names_in_db = set(InterpolData.objects.values_list("name", flat=True))
        
        # Get the names of all records currently present in RabbitMQ
        names_from_last_sync = self.get_current_interpol_names()

        # Identify names that are in the database but not in the latest Interpol updates
        removed_names = current_names_in_db - names_from_last_sync

        if removed_names:
            # Log a warning for records that are being removed
            self.stdout.write(self.style.WARNING(
                f"Removed records detected: {', '.join(removed_names)}"
            ))
            # Delete the removed records from the database
            InterpolData.objects.filter(name__in=removed_names).delete()
            self.stdout.write(self.style.SUCCESS("Removed records have been deleted."))

    def get_current_interpol_names(self):
        
        # Establish a connection to RabbitMQ
        connection_parameters = pika.ConnectionParameters('rabbitmq')
        connection = pika.BlockingConnection(connection_parameters)
        channel = connection.channel()
        
        # Declare the 'interpol-data' queue if it doesn't exist
        channel.queue_declare(queue='interpol-data')
        
        # Set to store unique names from RabbitMQ messages
        current_names = set()
        
        # Consume messages from the queue without waiting (basic_get)
        method_frame, _, body = channel.basic_get(queue='interpol-data', auto_ack=True)
        while method_frame:
            # Parse each message as JSON and add the 'Name' to the set
            data = json.loads(body)
            if "Name" in data:
                current_names.add(data["Name"])
            # Get the next message from the queue
            method_frame, _, body = channel.basic_get(queue='interpol-data', auto_ack=True)

        # Close the connection to RabbitMQ
        connection.close()
        return current_names
