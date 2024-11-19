import pika
import json
import os
import django

from interpol_app.models import InterpolData
import sys
sys.path.append('/app')  


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Interpol_Server.settings")

django.setup()

def callback(ch,method,properties,body):
    data = json.loads(body)
    interpol_data = InterpolData(
        name = data["name"],
        age = data["age"],
        nationality=data['nationality'],
        img_url = data['img_url']
    )
    interpol_data.save()
    print("Data saved to database",data)

def consume():
    connection_parameters = pika.ConnectionParameters('rabbitmq')
    connection = pika.BlockingConnection(connection_parameters)
    channel = connection.channel()
    channel.queue_declare(queue='interpol-data')

    channel.basic_consume(queue='interpol-data',on_message_callback=callback,auto_ack=True)
    print("Waiting for messages...")
    channel.start_consuming()