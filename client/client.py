import json, threading, socket

class MyThread(threading.Thread):
    def __init__(self, index):
        super(MyThread, self).__init__()
        self.index = index
        self.connection = None
        
    def run(self):
        s = socket.socket()
        s.connect(("localhost", self.index+8001))
        self.connection = s
        while True:
            data = self.connection.recv(1024)
            if not data:
                break
            else:
                message = data.decode()
                decoded_message = json.loads(message)
                print(f"Client {self.index} received: {decoded_message}")
                sending_message = f"Client {self.index} acknowledges receipt of {decoded_message}"
                encoded_message = json.dumps(sending_message)
                self.connection.sendall(encoded_message.encode())

def main():
    threads = []
    for i in range(4):
        t = MyThread(i)
        t.start()
        threads.append(t)
    
    for i in range(4):
        threads[i].join()
        threads[i].connection.close()
    
if __name__ == "__main__":
    main()