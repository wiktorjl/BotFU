from base_chat_bot import BaseChatBot
from openai import OpenAI
import os

class ChatGPTBot(BaseChatBot):
    def __init__(self, host='localhost', port=5000, bot_name='ChatGPT', context_file=None):
        super().__init__(host, port, bot_name, context_file)
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("Please set the OPENAI_API_KEY environment variable")
        self.client = OpenAI(api_key=api_key)

    def generate_response(self):
        try:
            self.print_system_message("Generating response...")
            messages = [
                {"role": "system", "content": self.character_context},
            ] + [{"role": "user" if i % 2 == 0 else "assistant", "content": msg} 
                 for i, msg in enumerate(self.conversation_history[-5:])]

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=150
            )

            generated_response = response.choices[0].message.content.strip()
            self.print_system_message(f"Response generated: {generated_response[:50]}...")
            return generated_response
        except Exception as e:
            self.print_error(f"Error generating response: {e}")
            return f"I'm sorry, I ({self.bot_name}) couldn't generate a response at this time."