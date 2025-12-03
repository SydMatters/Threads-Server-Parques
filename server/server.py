import threading
import socket
import json
from random import randint
#from dice import Dice

class MyThread(threading.Thread):
    def __init__(self, port):
        super(MyThread, self).__init__()
        self.socket = socket.socket()
        self.client = None
        self.address = None
        self.sending_message = ""
        self.received_message = ""
        self.port = port
        self.critical_section = 1 # Mientras sea 1 esta disponible, 0 en uso
        
    def create_socket(self):
        self.socket.bind(("localhost", int(self.port)))
        self.socket.listen(1)
        print(f"[Puerto {self.port}] Servidor activo, esperando conexión...")

    def receive_clients(self):
        self.client, self.address = self.socket.accept()
        print(f"[Puerto {self.port}] Conexión aceptada de {self.address}")
      
    def synchronize(self):
        pass

    def run(self):
        self.create_socket()
        self.receive_clients()
        self.client.close()
        self.socket.close()

def broadcast_message(clients, message):
    for client in clients:
        client.sendall(message.encode())
        
def Dice_roll():
    return randint(1, 6)
    
    
def main():
    threads = []
    clients = []
    messages = []
    port = 8001

    for i in range(4):  # Puedes aumentar el número de hilos aquí
        t = MyThread(port)
        threads.append(t)
        port += 1

    for t in threads:
        t.start()
        clients.append(t.client)
        
    
    i = 0
    j = 0
    
    while True:
        if i == 4:
            i = 0
            j += 1
        if j >= len(threads):
            break
        dice_results =[Dice_roll(), Dice_roll()]
        sending_message = json.dumps(dice_results)
        t[i].client.sendall(sending_message.encode())
        received_message = t[i].client.recv(1024).decode()
        decoded_message = json.loads(received_message)
        print(f"From client {i}: {decoded_message}")
        broadcast_message(clients, received_message)
        i += 1
        
    for t in threads:
        t.join()
        t.client.close()
        t.socket.close()
        #clients.append(t.client)

if __name__ == "__main__":
    main()