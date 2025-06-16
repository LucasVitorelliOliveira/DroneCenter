import grpc
from server.grpc_definitions import drone_pb2, drone_pb2_grpc

def listar_drones(stub):
    response = stub.ListDrones(drone_pb2.Empty())
    if not response.drones:
        print("Nenhum drone online.")
    else:
        print("\n--- Drones Online ---")
        for drone in response.drones:
            print(f"ID: {drone.drone_id} | Status: {drone.status}")
        print("---------------------")

def enviar_comando(stub):
    drone_id = input("ID do drone: ").strip()
    comando = input("Comando a enviar: ").strip()
    req = drone_pb2.CommandRequest(drone_id=drone_id, command=comando)
    resp = stub.SendCommand(req)
    print(f"↪ {resp.message}")

def main():
    channel = grpc.insecure_channel('localhost:50051')
    stub = drone_pb2_grpc.DroneControlStub(channel)

    while True:
        print("\n=== Central de Comando ===")
        print("1 - Listar drones")
        print("2 - Enviar comando")
        print("0 - Sair")
        op = input("Escolha: ").strip()

        if op == '1':
            listar_drones(stub)
        elif op == '2':
            enviar_comando(stub)
        elif op == '0':
            print("Encerrando Central.")
            break
        else:
            print("Opção inválida.")

if __name__ == "__main__":
    main()
