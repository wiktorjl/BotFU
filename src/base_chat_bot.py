import socket
import threading
import json
import os
import time
import random
from datetime import datetime
from colorama import init, Fore, Style
import textwrap
import sys

# Initialize colorama for cross-platform color support
init(autoreset=True)

class BaseChatBot:
    def __init__(self, host='localhost', port=5000, bot_name='Bot', context_file=None):
        self.host = host
        self.port = port
        self.bot_name = bot_name
        self.client_socket = None
        self.conversation_history = []
        self.character_context = self.load_context(context_file)
        self.last_sender = None
        self.response_generated = threading.Event()
        self.message_received = threading.Event()

    def load_context(self, context_file):
        if context_file and os.path.exists(context_file):
            with open(context_file, 'r') as file:
                return file.read().strip()
        return "You are a helpful AI assistant participating in a group chat. Keep your responses concise."

    def connect(self):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.print_system_message(f"Attempting to connect to {self.host}:{self.port}")
            self.client_socket.connect((self.host, self.port))
            self.print_system_message(f"Connected to server at {self.host}:{self.port}")
            
            self.print_system_message(f"Sending bot name: {self.bot_name}")
            self.client_socket.send(self.bot_name.encode('utf-8'))
            
            self.print_system_message(f"Starting receive_messages thread")
            receive_thread = threading.Thread(target=self.receive_messages)
            receive_thread.start()
            
            self.print_system_message(f"Connection process completed")
        except Exception as e:
            self.print_error(f"Error during connection: {e}")
            raise

    def receive_messages(self):
        buffer = ""
        self.print_system_message("Entered receive_messages loop")
        while True:
            try:
                chunk = self.client_socket.recv(1024).decode('utf-8')
                if not chunk:
                    self.print_system_message("Server closed the connection")
                    self.client_socket.close()
                    break
                
                buffer += chunk
                self.print_system_message(f"Received data: {buffer}")
                
                while '}' in buffer:
                    try:
                        json_end = buffer.index('}') + 1
                        json_str = buffer[:json_end]
                        buffer = buffer[json_end:]
                        
                        data = json.loads(json_str)
                        sender = data['sender']
                        content = data['message']
                        self.print_received_message(sender, content)
                        
                        self.conversation_history.append(f"Human: {sender}: {content}")
                        self.message_received.set()
                        
                        if sender != self.bot_name and sender != self.last_sender and sender != "SYSTEM":
                            self.last_sender = sender
                            self.print_system_message(f"Triggering response to {sender}")
                            threading.Thread(target=self.throttled_response).start()
                        else:
                            self.print_system_message(f"Ignoring message from {sender} (same as last sender, self, or SYSTEM)")
                    except json.JSONDecodeError as e:
                        self.print_error(f"JSON Decode Error: {e}")
                        self.print_error(f"Problematic JSON: {json_str}")
                        buffer = buffer[json_end:]
                    except ValueError:
                        break
            except Exception as e:
                self.print_error(f"An error occurred in receive_messages: {e}")
                self.print_error(f"Error details: {type(e).__name__}")
                self.client_socket.close()
                break
        self.print_system_message("Exited receive_messages loop")

    def throttled_response(self):
        delay = random.uniform(1, 5)
        self.print_system_message(f"Thinking for {delay:.2f} seconds...")
        time.sleep(delay)

        response = self.generate_response()
        if response:
            self.send_message(response)
        self.response_generated.set()

    def send_message(self, message):
        try:
            # Remove any leading/trailing whitespace and newlines
            message = message.strip()
            
            if not message:
                self.print_error("Attempted to send an empty message. Ignoring.")
                return

            # Split the message into chunks if it's too long
            max_chunk_size = 1000
            chunks = [message[i:i+max_chunk_size] for i in range(0, len(message), max_chunk_size)]
            
            for chunk in chunks:
                self.client_socket.send(chunk.encode('utf-8'))
                time.sleep(0.1)  # Small delay between chunks
            
            # Send a newline character to signal the end of the message
            self.client_socket.send('\n'.encode('utf-8'))
            
            # Add bot's message to conversation history
            self.conversation_history.append(f"Assistant: {message}")
            self.last_sender = self.bot_name  # Update last_sender to this bot
            self.print_sent_message(message)
        except Exception as e:
            self.print_error(f"Error sending message: {e}")

    def generate_response(self):
        raise NotImplementedError("Subclasses must implement generate_response method")

    def print_system_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{Fore.YELLOW}{Style.BRIGHT}[{timestamp}] SYSTEM: {message}{Style.RESET_ALL}")
        sys.stdout.flush()

    def print_received_message(self, sender, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{Fore.CYAN}{Style.BRIGHT}[{timestamp}] RECEIVED - {sender}:{Style.RESET_ALL}")
        self.print_formatted_message(message)
        sys.stdout.flush()

    def print_sent_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{Fore.GREEN}{Style.BRIGHT}[{timestamp}] SENT:{Style.RESET_ALL}")
        self.print_formatted_message(message)
        sys.stdout.flush()

    def print_formatted_message(self, message):
        paragraphs = message.split('\n')
        for paragraph in paragraphs:
            wrapped_lines = textwrap.wrap(paragraph, width=80, break_long_words=False, replace_whitespace=False)
            for line in wrapped_lines:
                print(f"  {line}")
            if len(paragraphs) > 1:
                print()
        sys.stdout.flush()

    def print_error(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{Fore.RED}{Style.BRIGHT}[{timestamp}] ERROR: {message}{Style.RESET_ALL}")
        sys.stdout.flush()