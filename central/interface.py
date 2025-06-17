import tkinter as tk
from tkinter import ttk
import subprocess
import threading
import sys
import docker
from threading import Thread


import grpc
from server.grpc_definitions import drone_pb2, drone_pb2_grpc
from shared.rabbitmq_config import consume_events

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

        self.grpc_channel = grpc.insecure_channel('localhost:50051')
        self.grpc_stub = drone_pb2_grpc.DroneControlStub(self.grpc_channel)

        def processar_evento(msg):
            print(f"[INTERFACE] Mensagem recebida: {msg}")
            if "OFFLINE" in msg:
                drone_id = msg.split(":::")[0]
                if drone_id in self.drone_labels:
                    self.drone_labels[drone_id].set("Status: OFFLINE\nPOS: (-,-)\nBATT: 0%")
                return

            if "POS=" in msg and "BATT=" in msg:
                try:
                    drone_id, dados = msg.split(":::")
                    pos = dados.split(";")[0].strip()
                    batt = dados.split(";")[1].strip()

                    status_text = f"Status: Online\n{pos}\n{batt}"
                    if drone_id in self.drone_labels:
                        self.drone_labels[drone_id].set(status_text)
                    else:
                        print(f"[AVISO] ID desconhecido: {drone_id}")
                except Exception as e:
                    print("[Erro ao processar evento]:", e)
        Thread(target=consume_events, args=(processar_evento,), daemon=True).start()

    def _build_status_area(self):
        self.start_button = ttk.Button(self.status_frame, text="Iniciar Sistemas", command=self.iniciar_sistemas)
        self.start_button.grid(row=0, column=0, padx=5, pady=5)

        self.stop_button = ttk.Button(self.status_frame, text="Desligar Sistemas", command=self.desligar_sistemas)
        self.stop_button.grid(row=0, column=1, padx=5)

        self.status_label = ttk.Label(self.status_frame, text="Aguardando inicialização...")
        self.status_label.grid(row=0, column=2, padx=5)

        # Novos indicadores
        label_names = {
            "server":          "Server",
            "simulator":       "Simulador",
            "rabbit_service":  "RabbitMQ",
            "rabbit_broker":   "Broker",
            "rabbit_consume":  "Consumo"
        }

        self.indicadores_status = {}

        col = 1
        for key, pretty in label_names.items():
            var   = tk.StringVar(value=f"🔴 {pretty}")
            label = tk.Label(self.status_frame, textvariable=var, fg="red", anchor="w")
            label.grid(row=1, column=col, sticky="w", padx=10)
            self.indicadores_status[key] = (var, label, pretty)   # ← guardo var, label e nome bonitinho
            col += 1

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
                from shared.rabbitmq_config import wait_for_rabbitmq_ready

                client = docker.from_env()
                container_name = "drone-rabbitmq"

                try:
                    container = client.containers.get(container_name)
                    if container.status != "running":
                        container.start()
                        print("✔️ RabbitMQ iniciado")
                    else:
                        print("🐇 RabbitMQ já em execução")
                except docker.errors.NotFound:
                    print("🆕 Criando container RabbitMQ")
                    client.containers.run(
                        "rabbitmq:3-management",
                        detach=True,
                        ports={"5672/tcp": 5672, "15672/tcp": 15672},
                        name=container_name,
                        hostname="drone-rabbit",
                    )
                    print("🆕 RabbitMQ container criado e iniciado")

                # Aguardar RabbitMQ estar funcional (porta 5672 ativa)
                from shared.rabbitmq_config import wait_for_rabbitmq_ready
                if not wait_for_rabbitmq_ready():
                    self.status_label.config(text="Erro: RabbitMQ não respondeu a tempo.")
                    return

            except Exception as e:
                print(f"[ERRO ao iniciar RabbitMQ]: {e}")
                self.status_label.config(text="Erro ao iniciar RabbitMQ")
                return

            # Iniciar servidor e simulador
            try:
                self.server_proc = subprocess.Popen([python_exec, "-m", "server.server"])
                self.sim_proc = subprocess.Popen([python_exec, "-m", "simulator.simulator"])
                print("✔️ Servidor e simulador iniciados")
                self.status_label.config(text="Sistemas iniciados ✅")

                self.set_indicator("server", True)
                self.set_indicator("simulator", True)
                self.set_indicator("rabbit_service", True)
                self.set_indicator("rabbit_broker", True)

            except Exception as e:
                print(f"[ERRO ao iniciar server/sim]: {e}")
                self.status_label.config(text="Erro ao iniciar subprocessos")

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

            for key in self.indicadores_status:
                self.set_indicator(key, False)

        threading.Thread(target=stop, daemon=True).start()

    def enviar_comando(self):
        drone_id = self.selected_drone.get()
        coords = self.coord_entry.get().strip()

        try:
            request = drone_pb2.CommandRequest(
                drone_id=drone_id,
                command=f"vá para ({coords})"
            )
            response = self.grpc_stub.SendCommand(request)
            self.log_box.insert(tk.END, f"✅ {response.message}\n")
        except Exception as e:
            self.log_box.insert(tk.END, f"❌ Erro ao enviar comando: {e}\n")

    def set_indicator(self, key, online: bool):
        """
        Atualiza texto e cor do indicador.
        online=True  👉 🟢 + verde
        online=False 👉 🔴 + vermelho
        """
        def _update():
            if key in self.indicadores_status:
                var, lbl, pretty = self.indicadores_status[key]
                emoji  = "🟢" if online else "🔴"
                color  = "green" if online else "red"
                var.set(f"{emoji} {pretty}")
                lbl.config(fg=color)
        self.master.after(0, _update)   # garante execução na thread do Tk

if __name__ == "__main__":
    root = tk.Tk()
    app = DroneControlGUI(root)
    root.mainloop()
