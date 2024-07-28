import argparse
import time
from claude import ClaudeBot
from chatgpt import ChatGPTBot

def start_bot(bot_class, bot_name, context_file):
    bot = bot_class(bot_name=bot_name, context_file=context_file)
    try:
        bot.connect()
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

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
    parser = argparse.ArgumentParser(description="Start a chat bot instance")
    parser.add_argument("bot_type", type=str, choices=["claude", "chatgpt"], help="Type of bot to start")
    parser.add_argument("bot_name", type=str, help="Name for this bot instance")
    parser.add_argument("--context", type=str, help="Path to the character context file")
    args = parser.parse_args()

    bot_class = ClaudeBot if args.bot_type == "claude" else ChatGPTBot
    start_bot(bot_class, args.bot_name, args.context)