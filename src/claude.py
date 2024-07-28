import socket
import threading
import json
import os
import argparse
import time
import random
from datetime import datetime
from colorama import init, Fore, Style
import anthropic
import textwrap
import sys

# Initialize colorama for cross-platform color support
init(autoreset=True)

class ClaudeBot:
    def __init__(self, host='localhost', port=5000, bot_name='Claude', context_file=None):
        self.host = host
        self.port = port
        self.bot_name = bot_name
        self.client_socket = None
        self.conversation_history = []
        self.character_context = self.load_context(context_file)
        self.last_sender = None  # Track the last message sender
        self.response_generated = threading.Event()
        self.message_received = threading.Event()

        # Set up Anthropic client
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("Please set the ANTHROPIC_API_KEY environment variable")
        self.client = anthropic.Anthropic(api_key=api_key)

    def load_context(self, context_file):
        if context_file and os.path.exists(context_file):
            with open(context_file, 'r') as file:
                return file.read().strip()
        return "You are Claude, an AI assistant created by Anthropic to be helpful, harmless, and honest. You are participating in a group chat. Keep your responses concise."

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
                
                # Process all complete JSON objects in the buffer
                while '}' in buffer:
                    try:
                        json_end = buffer.index('}') + 1
                        json_str = buffer[:json_end]
                        buffer = buffer[json_end:]
                        
                        data = json.loads(json_str)
                        sender = data['sender']
                        content = data['message']
                        self.print_received_message(sender, content)
                        
                        # Add the received message to conversation history
                        self.conversation_history.append(f"Human: {sender}: {content}")
                        
                        # Set the message_received event
                        self.message_received.set()
                        
                        # Only generate a response if the message is not from this bot and not from the last sender
                        if sender != self.bot_name and sender != self.last_sender and sender != "SYSTEM":
                            self.last_sender = sender
                            self.print_system_message(f"Triggering response to {sender}")
                            # Generate a response using Claude (with throttling)
                            threading.Thread(target=self.throttled_response).start()
                        else:
                            self.print_system_message(f"Ignoring message from {sender} (same as last sender, self, or SYSTEM)")
                    except json.JSONDecodeError as e:
                        self.print_error(f"JSON Decode Error: {e}")
                        self.print_error(f"Problematic JSON: {json_str}")
                        # Move past this problematic JSON object
                        buffer = buffer[json_end:]
                    except ValueError:
                        # If we can't find a complete JSON object, break the loop
                        break
            except Exception as e:
                self.print_error(f"An error occurred in receive_messages: {e}")
                self.print_error(f"Error details: {type(e).__name__}")
                self.client_socket.close()
                break
        self.print_system_message("Exited receive_messages loop")

    def throttled_response(self):
        # Random delay between 1 and 5 seconds
        delay = random.uniform(1, 5)
        self.print_system_message(f"Thinking for {delay:.2f} seconds...")
        time.sleep(delay)

        response = self.generate_response()
        if response:
            self.send_message(response)
        self.response_generated.set()

    def send_message(self, message):
        try:
            # Split the message into chunks if it's too long
            max_chunk_size = 1000  # Adjust this value as needed
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
        try:
            self.print_system_message("Generating response...")
            # Prepare the conversation for the API call
            conversation = self.character_context + "\n\n" + "\n".join(self.conversation_history[-5:])

            # Call the Anthropic API
            response = self.client.completions.create(
                model="claude-2.1",
                prompt=f"{anthropic.HUMAN_PROMPT} {conversation}{anthropic.AI_PROMPT}",
                max_tokens_to_sample=300,
                temperature=0.7,
                stop_sequences=[anthropic.HUMAN_PROMPT]
            )

            # Extract the generated message
            generated_response = response.completion.strip()
            self.print_system_message(f"Response generated: {generated_response[:50]}...")
            return generated_response
        except Exception as e:
            self.print_error(f"Error generating response: {e}")
            return f"I'm sorry, I ({self.bot_name}) couldn't generate a response at this time."

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
        sys.stdout.flush()

    def print_error(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{Fore.RED}{Style.BRIGHT}[{timestamp}] ERROR: {message}{Style.RESET_ALL}")
        sys.stdout.flush()

def start_bot(bot_name, context_file):
    bot = ClaudeBot(bot_name=bot_name, context_file=context_file)
    try:
        bot.connect()
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    # Keep the main thread running
    try:
        while True:
            time.sleep(1)
            if bot.message_received.is_set():
                if not bot.response_generated.is_set():
                    bot.print_system_message("Waiting for response...")
                bot.message_received.clear()
                bot.response_generated.clear()
            else:
                bot.print_system_message("Waiting for message...")
    except KeyboardInterrupt:
        bot.print_system_message("Bot is disconnecting...")
        if bot.client_socket:
            bot.client_socket.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start a Claude bot instance")
    parser.add_argument("bot_name", type=str, help="Name for this bot instance")
    parser.add_argument("--context", type=str, help="Path to the character context file")
    args = parser.parse_args()

    start_bot(args.bot_name, args.context)