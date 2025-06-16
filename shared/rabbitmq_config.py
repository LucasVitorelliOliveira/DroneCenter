import time
import pika
import socket

RABBITMQ_QUEUE = 'drone_events'

def get_connection(retries=5, delay=2):
    credentials = pika.PlainCredentials('guest', 'guest')
    parameters = pika.ConnectionParameters(
        host='localhost',
        port=5672,
        credentials=credentials,
        heartbeat=60,
        blocked_connection_timeout=5
    )

    for attempt in range(retries):
        try:
            return pika.BlockingConnection(parameters)
        except Exception as e:
            print(f"[RabbitMQ ERRO - conexão tentativa {attempt+1}] {e}")
            time.sleep(delay)
    print("[RabbitMQ] Todas as tentativas de conexão falharam.")
    return None

def publish_event(message: str):
    conn = get_connection()
    if not conn:
        return
    try:
        channel = conn.channel()
        channel.queue_declare(queue="drone_events")
        channel.basic_publish(exchange='', routing_key="drone_events", body=message.encode())
    except Exception as e:
        print("[RabbitMQ ERRO - publish]", e)
    finally:
        conn.close()

def consume_events(callback):
    from shared.rabbitmq_config import wait_for_rabbitmq_ready
    if not wait_for_rabbitmq_ready():
        print("[RabbitMQ] Não está pronto. Abortando consumo.")
        return

    conn = get_connection()
    if not conn:
        print("[RabbitMQ] Conexão falhou")
        return
    try:
        channel = conn.channel()
        channel.queue_declare(queue="drone_events")

        def on_message(ch, method, properties, body):
            callback(body.decode())

        channel.basic_consume(queue="drone_events", on_message_callback=on_message, auto_ack=True)
        print("[RabbitMQ] Escutando eventos...\n")
        channel.start_consuming()
    except Exception as e:
        print("[RabbitMQ ERRO - consume]", e)

def wait_for_rabbitmq_ready(host='localhost', port=5672, timeout=60):
    print("[RabbitMQ] Aguardando RabbitMQ ficar pronto...")
    start_time = time.time()
    
    # Passo 1: aguarda porta 5672 estar aberta
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection((host, port), timeout=2):
                print("[RabbitMQ] Porta 5672 acessível")
                break
        except (OSError, ConnectionRefusedError):
            time.sleep(1)
    else:
        print("[RabbitMQ] Porta 5672 inacessível após timeout")
        return False

    # Passo 2: tenta conexão real com pika
    for tentativa in range(10):
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
            connection.close()
            print("[RabbitMQ] Broker funcional ✅")
            return True
        except pika.exceptions.AMQPConnectionError as e:
            print(f"[RabbitMQ] Broker ainda não pronto ({tentativa+1}/10): {e}")
            time.sleep(5)

    print("[RabbitMQ] Broker não respondeu corretamente.")
    return False