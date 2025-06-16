import tkinter as tk
from tkinter import ttk
import subprocess
import threading
import sys
import docker

class DroneControlGUI:
    def __init__(self, master):
        self.master = master
        master.title("Central de Comando de Drones")
        master.geometry("800x500")

        self.status_frame = ttk.LabelFrame(master, text="Status do Sistema")
        self.status_frame.pack(fill="x", padx=10, pady=5)

        self.drone_frame = ttk.LabelFrame(master, text="Drones")
        self.drone_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.command_frame = ttk.LabelFrame(master, text="Enviar Comando")
        self.command_frame.pack(fill="x", padx=10, pady=5)

        self._build_status_area()
        self._build_drone_displays()
        self._build_command_area()

    def _build_status_area(self):
        self.start_button = ttk.Button(self.status_frame, text="Iniciar Sistemas", command=self.iniciar_sistemas)
        self.start_button.pack(side="left", padx=10, pady=5)

        self.stop_button = ttk.Button(self.status_frame, text="Desligar Sistemas", command=self.desligar_sistemas)
        self.stop_button.pack(side="left", padx=10)

        self.status_label = ttk.Label(self.status_frame, text="Aguardando inicialização...")
        self.status_label.pack(side="left", padx=10)

    def _build_drone_displays(self):
        self.drone_labels = {}
        for i in range(3):
            drone_id = f"drone-{i+1}"
            frame = ttk.LabelFrame(self.drone_frame, text=drone_id, width=200, height=100)
            frame.pack(side="left", padx=10, pady=10, expand=True, fill="both")

            status_text = tk.StringVar()
            status_text.set("Status: Offline\nPOS: (-,-)\nBATT: --%")

            label = tk.Label(frame, textvariable=status_text, justify="left", anchor="w", font=("Courier", 10))
            label.pack(fill="both", expand=True, padx=5, pady=5)

            self.drone_labels[drone_id] = status_text

    def _build_command_area(self):
        self.selected_drone = tk.StringVar()
        self.selected_drone.set("drone-1")

        self.drone_selector = ttk.Combobox(self.command_frame, textvariable=self.selected_drone, values=[f"drone-{i+1}" for i in range(3)])
        self.drone_selector.pack(side="left", padx=10)

        self.coord_entry = ttk.Entry(self.command_frame)
        self.coord_entry.pack(side="left", padx=10)
        self.coord_entry.insert(0, "x,y")

        self.send_button = ttk.Button(self.command_frame, text="Enviar para", command=self.enviar_comando)
        self.send_button.pack(side="left", padx=10)

        self.log_box = tk.Text(self.command_frame, height=5, width=50)
        self.log_box.pack(side="left", padx=10)

    def iniciar_sistemas(self):
        self.status_label.config(text="Inicializando sistemas...")

        def start():
            python_exec = sys.executable 

            # Iniciar RabbitMQ via Docker
            try:
                client = docker.from_env()
                container_name = "drone-rabbitmq"

                # Verifica se o container existe
                try:
                    container = client.containers.get(container_name)
                    if container.status != "running":
                        container.start()
                        print("✔️ RabbitMQ iniciado")
                except docker.errors.NotFound:
                    # Cria e inicia o container
                    client.containers.run(
                        "rabbitmq:3-management",
                        detach=True,
                        ports={"5672/tcp": 5672, "15672/tcp": 15672},
                        name=container_name,
                        hostname="drone-rabbit",
                    )
                    print("🆕 RabbitMQ container criado e iniciado")

            except Exception as e:
                print(f"[ERRO ao iniciar RabbitMQ]: {e}")

                subprocess.Popen([python_exec, "-m", "server.server"])
                subprocess.Popen([python_exec, "-m", "simulator.simulator"])
                self.status_label.config(text="Sistemas iniciados ✅")

        threading.Thread(target=start, daemon=True).start()

    def desligar_sistemas(self):
        self.status_label.config(text="Encerrando sistemas...")

        def stop():
            # Finaliza subprocessos
            try:
                if hasattr(self, "server_proc"):
                    self.server_proc.terminate()
                    print("⛔ Servidor encerrado")
                if hasattr(self, "sim_proc"):
                    self.sim_proc.terminate()
                    print("⛔ Simulador encerrado")
            except Exception as e:
                print(f"[ERRO ao encerrar subprocessos]: {e}")

            # Encerra RabbitMQ via Docker
            try:
                client = docker.from_env()
                container = client.containers.get("drone-rabbitmq")
                container.stop()
                print("🛑 RabbitMQ parado")
            except Exception as e:
                print(f"[ERRO ao parar RabbitMQ]: {e}")

            self.status_label.config(text="Sistemas desligados ❌")

        threading.Thread(target=stop, daemon=True).start()

    def enviar_comando(self):
        drone_id = self.selected_drone.get()
        coords = self.coord_entry.get().strip()
        self.log_box.insert(tk.END, f"📤 Enviando para {drone_id}: {coords}\n")

if __name__ == "__main__":
    root = tk.Tk()
    app = DroneControlGUI(root)
    root.mainloop()
