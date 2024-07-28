import socket
import threading
import json
import os
import argparse
import time
import random
from datetime import datetime
from colorama import init, Fore, Style
from openai import OpenAI
import textwrap

# Initialize colorama for cross-platform color support
init(autoreset=True)

class ChatGPTBot:
    def __init__(self, host='localhost', port=5000, bot_name='ChatGPT', context_file=None):
        self.host = host
        self.port = port
        self.bot_name = bot_name
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conversation_history = []
        self.character_context = self.load_context(context_file)
        self.last_sender = None  # Track the last message sender

        # Set up OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("Please set the OPENAI_API_KEY environment variable")
        self.client = OpenAI(api_key=api_key)

    def load_context(self, context_file):
        if context_file and os.path.exists(context_file):
            with open(context_file, 'r') as file:
                return file.read().strip()
        return "You are a helpful assistant in a group chat. Keep your responses concise."

    def connect(self):
        self.client_socket.connect((self.host, self.port))
        self.client_socket.send(self.bot_name.encode('utf-8'))
        self.print_system_message(f"Connected to server as {self.bot_name}")
        receive_thread = threading.Thread(target=self.receive_messages)
        receive_thread.start()

    def receive_messages(self):
        while True:
            try:
                message = self.client_socket.recv(1024).decode('utf-8')
                if message:
                    try:
                        data = json.loads(message)
                        sender = data['sender']
                        content = data['message']
                        self.print_received_message(sender, content)
                        
                        # Add the received message to conversation history
                        self.conversation_history.append({"role": "user", "content": f"{sender}: {content}"})
                        
                        # Only generate a response if the message is not from this bot
                        if sender != self.bot_name and sender != self.last_sender:
                            self.last_sender = sender
                            # Generate a response using ChatGPT (with throttling)
                            threading.Thread(target=self.throttled_response).start()
                        else:
                            self.print_system_message(f"Ignoring message from {sender} (same as last sender or self)")
                    except json.JSONDecodeError as e:
                        self.print_error(f"JSON Decode Error: {e}")
                        self.print_error(f"Problematic message: {message}")
                else:
                    self.print_system_message("Disconnected from server")
                    self.client_socket.close()
                    break
            except Exception as e:
                self.print_error(f"An error occurred: {e}")
                self.print_error(f"Error details: {type(e).__name__}")
                self.client_socket.close()
                break

    def throttled_response(self):
        # Random delay between 1 and 5 seconds
        delay = random.uniform(1, 5)
        self.print_system_message(f"Thinking for {delay:.2f} seconds...")
        time.sleep(delay)

        response = self.generate_response()
        self.send_message(response)

    def send_message(self, message):
        try:
            self.client_socket.send(message.encode('utf-8'))
            # Add bot's message to conversation history
            self.conversation_history.append({"role": "assistant", "content": message})
            self.last_sender = self.bot_name  # Update last_sender to this bot
            self.print_sent_message(message)
        except Exception as e:
            self.print_error(f"Error sending message: {e}")

    def generate_response(self):
        try:
            # Prepare the messages for the API call
            messages = [
                {"role": "system", "content": self.character_context},
            ] + self.conversation_history[-5:]  # Include only the last 5 messages for context

            # Call the OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=150  # Limit the response length
            )

            # Extract the generated message
            return response.choices[0].message.content.strip()
        except Exception as e:
            self.print_error(f"Error generating response: {e}")
            return f"I'm sorry, I ({self.bot_name}) couldn't generate a response at this time."

    def print_system_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{Fore.YELLOW}{Style.BRIGHT}[{timestamp}] SYSTEM: {message}{Style.RESET_ALL}")

    def print_received_message(self, sender, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{Fore.CYAN}{Style.BRIGHT}[{timestamp}] RECEIVED - {sender}:{Style.RESET_ALL}")
        self.print_formatted_message(message)

    def print_sent_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{Fore.GREEN}{Style.BRIGHT}[{timestamp}] SENT:{Style.RESET_ALL}")
        self.print_formatted_message(message)

    def print_formatted_message(self, message):
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

    def print_error(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{Fore.RED}{Style.BRIGHT}[{timestamp}] ERROR: {message}{Style.RESET_ALL}")

def start_bot(bot_name, context_file):
    bot = ChatGPTBot(bot_name=bot_name, context_file=context_file)
    bot.connect()

    # Keep the main thread running
    try:
        while True:
            pass
    except KeyboardInterrupt:
        bot.print_system_message("Bot is disconnecting...")
        bot.client_socket.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start a ChatGPT bot instance")
    parser.add_argument("bot_name", type=str, help="Name for this bot instance")
    parser.add_argument("--context", type=str, help="Path to the character context file")
    args = parser.parse_args()

    start_bot(args.bot_name, args.context)