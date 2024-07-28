import socket
import threading
import json

class ChatClient:
    def __init__(self, host='localhost', port=5000):
        self.host = host
        self.port = port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self, username):
        self.client_socket.connect((self.host, self.port))
        self.client_socket.send(username.encode('utf-8'))
        receive_thread = threading.Thread(target=self.receive_messages)
        receive_thread.start()

    def send_message(self, message):
        self.client_socket.send(message.encode('utf-8'))

    def receive_messages(self):
        while True:
            try:
                message = self.client_socket.recv(1024).decode('utf-8')
                if message:
                    data = json.loads(message)
                    print(f"{data['sender']}: {data['message']}")
                else:
                    print("Disconnected from server")
                    self.client_socket.close()
                    break
            except:
                print("An error occurred!")
                self.client_socket.close()
                break

def start_client():
    client = ChatClient()
    username = input("Enter your username: ")
    client.connect(username)

    while True:
        message = input()
        if message.lower() == 'quit':
            break
        client.send_message(message)

    client.client_socket.close()

if __name__ == "__main__":
    start_client()