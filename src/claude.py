from base_chat_bot import BaseChatBot
import anthropic
import os

class ClaudeBot(BaseChatBot):
    def __init__(self, host='localhost', port=5000, bot_name='Claude', context_file=None):
        super().__init__(host, port, bot_name, context_file)
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("Please set the ANTHROPIC_API_KEY environment variable")
        self.client = anthropic.Anthropic(api_key=api_key)

    def generate_response(self):
        try:
            self.print_system_message("Generating response...")
            conversation = self.character_context + "\n\n" + "\n".join(self.conversation_history[-5:])

            response = self.client.completions.create(
                model="claude-2.1",
                prompt=f"{anthropic.HUMAN_PROMPT} {conversation}{anthropic.AI_PROMPT}",
                max_tokens_to_sample=300,
                temperature=0.7,
                stop_sequences=[anthropic.HUMAN_PROMPT]
            )

            generated_response = response.completion.strip()
            self.print_system_message(f"Response generated: {generated_response[:50]}...")
            return generated_response
        except Exception as e:
            self.print_error(f"Error generating response: {e}")
            return f"I'm sorry, I ({self.bot_name}) couldn't generate a response at this time."