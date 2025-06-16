import grpc
from concurrent import futures
import threading

from grpc_definitions import drone_pb2, drone_pb2_grpc 
import socket_handler
import pika

# --- CONFIGURAÇÕES RABBITMQ --- #
RABBITMQ_QUEUE = "drone_events"

def publish_event(message):
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()
        channel.queue_declare(queue=RABBITMQ_QUEUE)
        channel.basic_publish(exchange='', routing_key=RABBITMQ_QUEUE, body=message)
        connection.close()
    except Exception as e:
        print("[RabbitMQ ERRO]", e)

# --- SERVIÇO gRPC --- #
class DroneControlService(drone_pb2_grpc.DroneControlServicer):
    def SendCommand(self, request, context):
        success = socket_handler.send_command_to_drone(request.drone_id, request.command)
        print(f"[DEBUG] Tentando enviar comando para: '{request.drone_id}'")
        if success:
            msg = f"Comando '{request.command}' enviado ao drone {request.drone_id}"
            publish_event(f"[COMANDO] {msg}")
            return drone_pb2.CommandResponse(success=True, message=msg)
        else:
            return drone_pb2.CommandResponse(success=False, message="Drone não encontrado")

    def ListDrones(self, request, context):
        drones = socket_handler.list_drones()
        drone_list = [drone_pb2.DroneInfo(drone_id=d, status="online") for d in drones]
        return drone_pb2.DroneList(drones=drone_list)

# --- MAIN --- #
def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    drone_pb2_grpc.add_DroneControlServicer_to_server(DroneControlService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("[gRPC] Servidor gRPC rodando na porta 50051")
    server.wait_for_termination()

if __name__ == "__main__":
    threading.Thread(target=socket_handler.start_socket_server, daemon=True).start()
    serve()
