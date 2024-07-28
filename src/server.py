import socket
import threading
import json
from datetime import datetime
from colorama import init, Fore, Back, Style
import textwrap

# Initialize colorama for cross-platform color support
init()

class ChatServer:
    def __init__(self, host='localhost', port=5000):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = {}

    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        self.print_server_message(f"Server started on {self.host}:{self.port}")
        
        while True:
            client_socket, address = self.server_socket.accept()
            client_thread = threading.Thread(target=self.handle_client, args=(client_socket, address))
            client_thread.start()

    def handle_client(self, client_socket, address):
        username = client_socket.recv(1024).decode('utf-8')
        self.clients[username] = client_socket
        self.print_server_message(f"{username} connected from {address}")

        self.broadcast_system_message(f"{username} has joined the chat.")

        while True:
            try:
                message = client_socket.recv(1024).decode('utf-8')
                if message:
                    self.broadcast(username, message)
                else:
                    self.remove_client(username)
                    break
            except:
                self.remove_client(username)
                break

    def broadcast(self, sender, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        for username, client_socket in self.clients.items():
            if username != sender:
                try:
                    client_socket.send(json.dumps({"sender": sender, "message": message}).encode('utf-8'))
                except:
                    self.remove_client(username)
        
        self.print_chat_message(timestamp, sender, message)

    def broadcast_system_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        for username, client_socket in self.clients.items():
            try:
                client_socket.send(json.dumps({"sender": "SYSTEM", "message": message}).encode('utf-8'))
            except:
                self.remove_client(username)
        
        self.print_system_message(timestamp, message)

    def remove_client(self, username):
        if username in self.clients:
            self.clients[username].close()
            del self.clients[username]
            self.print_server_message(f"{username} disconnected")
            self.broadcast_system_message(f"{username} has left the chat.")

    def print_server_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{Fore.YELLOW}{Style.BRIGHT}[{timestamp}] SERVER: {message}{Style.RESET_ALL}")

    def print_system_message(self, timestamp, message):
        print(f"{Fore.CYAN}{Style.BRIGHT}[{timestamp}] SYSTEM: {message}{Style.RESET_ALL}")

    def print_chat_message(self, timestamp, sender, message):
        sender_color = Fore.GREEN if sender.startswith("ChatGPT") else Fore.BLUE
        print(f"{Style.DIM}[{timestamp}]{Style.RESET_ALL} {sender_color}{Style.BRIGHT}{sender}:{Style.RESET_ALL}")
        
        # Split message into paragraphs
        paragraphs = message.split('\n')
        
        for paragraph in paragraphs:
            # Wrap each paragraph to 80 characters
            wrapped_lines = textwrap.wrap(paragraph, width=80, break_long_words=False, replace_whitespace=False)
            
            # Print each wrapped line with proper indentation
            for line in wrapped_lines:
                print(f"  {line}")
            
            # Add a blank line between paragraphs for readability
            if len(paragraphs) > 1:
                print()

if __name__ == "__main__":
    server = ChatServer()
    server.start()