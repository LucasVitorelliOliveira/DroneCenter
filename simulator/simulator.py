import socket
import threading
import time
import random

# Configurações
SERVER_HOST = 'localhost'
SERVER_PORT = 9000

# Simula um drone
class Drone(threading.Thread):
    def __init__(self, drone_id):
        super().__init__()
        self.drone_id = drone_id
        self.running = True
        self.conn = None

        self.pos_x = random.randint(0, 100)
        self.pos_y = random.randint(0, 100)
        self.battery = random.randint(30, 100)

    def connect(self):
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn.connect((SERVER_HOST, SERVER_PORT))
        self.conn.sendall(self.drone_id.encode())
        time.sleep(1)  # Aguarda o servidor processar a conexão
        print(f"[{self.drone_id}] Conectado ao servidor")

    def run(self):
        self.connect()
        # Simula envio de dados periódicos
        while self.running and self.battery > 0:
            try:
               # Atualiza posição (±1 ou 0)
                self.pos_x += random.choice([-1, 0, 1])
                self.pos_y += random.choice([-1, 0, 1])

                # Garante que fique no espaço 0–100
                self.pos_x = max(0, min(100, self.pos_x))
                self.pos_y = max(0, min(100, self.pos_y))

                # Diminui a bateria
                self.battery -= 1

                status_msg = f"POS=({self.pos_x},{self.pos_y}); BATT={self.battery}%"
                self.conn.sendall(status_msg.encode())

                # Verifica se há comandos recebidos do servidor
                self.conn.settimeout(1.0)
                try:
                    data = self.conn.recv(1024)
                    if data:
                        print(f"[{self.drone_id}] RECEBEU COMANDO: {data.decode()}")
                except socket.timeout:
                    pass  # Sem comandos

                time.sleep(2)
            except Exception as e:
                print(f"[{self.drone_id}] ERRO: {e}")
                self.running = False

            offline_msg = "OFFLINE"
            try:
                self.conn.sendall(offline_msg.encode())
            except:
                pass 
        self.conn.close()

def iniciar_simulacao(numero_drones=3):
    drones = []
    for i in range(numero_drones):
        drone = Drone(drone_id=f"drone-{i+1}")
        drone.start()
        drones.append(drone)
    return drones

if __name__ == "__main__":
    iniciar_simulacao()
