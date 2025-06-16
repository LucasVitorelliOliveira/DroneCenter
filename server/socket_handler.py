import socket
import threading


from shared.rabbitmq_config import publish_event

# Mapeia drones conectados
connected_drones = {}

def handle_drone_connection(conn, addr):
    try:
        drone_id = conn.recv(1024).decode().strip()
        print(f"[DEBUG] Registrando drone com ID: '{drone_id}'")
        connected_drones[drone_id] = conn
        print(f"[SOCKET] Drone {drone_id} conectado de {addr}")
        while True:
            data = conn.recv(1024)
            if not data:
                break

            mensagem = data.decode().strip()
            print(f"[SOCKET] {drone_id} diz: {mensagem}")
            publish_event(f"{drone_id}:::{mensagem}")
    except Exception as e:
        print(f"[ERRO] Drone {addr} caiu: {e}")
    finally:
        if drone_id in connected_drones:
            del connected_drones[drone_id]
        conn.close()

def start_socket_server(host='0.0.0.0', port=9000):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen()
    print(f"[SOCKET] Servidor escutando em {host}:{port}")
    while True:
        conn, addr = server_socket.accept()
        threading.Thread(target=handle_drone_connection, args=(conn, addr), daemon=True).start()

def send_command_to_drone(drone_id, command):
    conn = connected_drones.get(drone_id)
    if conn:
        try:
            conn.sendall(command.encode())
            return True
        except:
            return False
    return False

def list_drones():
    return list(connected_drones.keys())
