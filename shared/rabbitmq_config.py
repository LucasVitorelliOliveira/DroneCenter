import pika

RABBITMQ_QUEUE = 'drone_events'

def get_connection():
    return pika.BlockingConnection(pika.ConnectionParameters('localhost'))

def publish_event(message: str):
    try:
        connection = get_connection()
        channel = connection.channel()
        channel.queue_declare(queue=RABBITMQ_QUEUE)
        channel.basic_publish(exchange='', routing_key=RABBITMQ_QUEUE, body=message.encode())
        connection.close()
    except Exception as e:
        print("[RabbitMQ ERRO - publish]", e)

def consume_events(callback):
    try:
        connection = get_connection()
        channel = connection.channel()
        channel.queue_declare(queue=RABBITMQ_QUEUE)

        def on_message(ch, method, properties, body):
            callback(body.decode())

        channel.basic_consume(queue=RABBITMQ_QUEUE, on_message_callback=on_message, auto_ack=True)
        print("[RabbitMQ] Aguardando eventos...\n")
        channel.start_consuming()
    except Exception as e:
        print("[RabbitMQ ERRO - consume]", e)
