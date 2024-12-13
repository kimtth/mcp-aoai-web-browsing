import asyncio
import os
from tkinter import Tk, Text, Button, Scrollbar, VERTICAL, RIGHT, Y, END, Frame
from dotenv import load_dotenv
from client_bridge.config import BridgeConfig, LLMConfig
from client_bridge.bridge import BridgeManager
from server.browser_navigator_server import BrowserNavigationServer
from loguru import logger

# Load environment variables
load_dotenv()

class ClientBridgeGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Client Bridge GUI")
        
        # Frame for the text area and scrollbar
        self.chat_frame = Frame(master)
        self.chat_frame.pack(padx=10, pady=10, fill='both', expand=True)

        # Set up the text area for chat history (readonly)
        self.text_area = Text(self.chat_frame, wrap='word', height=20, width=50, state='disabled')
        self.text_area.pack(side='left', fill='both', expand=True)

        # Scrollbar for the text area
        self.scrollbar = Scrollbar(self.chat_frame, command=self.text_area.yview, orient=VERTICAL)
        self.scrollbar.pack(side=RIGHT, fill=Y)
        self.text_area.config(yscrollcommand=self.scrollbar.set)

        # Frame for the user input and button
        self.input_frame = Frame(master)
        self.input_frame.pack(padx=10, pady=10, fill='x')

        # Text widget for the user input (editable)
        self.user_input = Text(self.input_frame, height=3, wrap='word', width=50)
        self.user_input.pack(side='left', fill='x', expand=True)

        # Send button
        self.send_button = Button(self.input_frame, text="Send", command=self.process_input)
        self.send_button.pack(side='right')

        # Set up configuration for server and bridge
        self.server = BrowserNavigationServer()
        self.config = BridgeConfig(
            mcp=self.server,
            llm_config=LLMConfig(
                azure_endpoint=os.getenv("AZURE_OPEN_AI_ENDPOINT"),
                api_version=os.getenv("AZURE_OPEN_AI_API_VERSION"),
                api_key=os.getenv("AZURE_OPEN_AI_API_KEY"),
                deploy_name=os.getenv("AZURE_OPEN_AI_DEPLOYMENT_MODEL")
            ),
            system_prompt="You are a helpful assistant that can use tools to help answer questions."
        )
        
        logger.info(f"Starting bridge with model: {self.config.llm_config.deploy_name}")
        
        # Initialize the bridge asynchronously
        asyncio.run(self.initialize_bridge())

    async def initialize_bridge(self):
        """Initialize the bridge manager for communication."""
        async with BridgeManager(self.config) as bridge:
            self.bridge = bridge
            logger.info("Bridge initialized successfully.")

    async def process_message(self, user_input):
        """Process the message using the bridge and return the response."""
        response = await self.bridge.process_message(user_input)
        return response

    def process_input(self):
        """Handle user input and trigger asynchronous processing."""
        user_input = self.user_input.get("1.0", END).strip()
        if user_input:
            # Display the user input in the chat area
            self.display_message(f"You: {user_input}\n")
            self.user_input.delete("1.0", END)

            # Run the asynchronous input handler
            asyncio.run(self.handle_input(user_input))

    async def handle_input(self, user_input):
        """Handle user input asynchronously and display response."""
        try:
            response = await self.process_message(user_input)
            self.display_message(f"Response: {response}\n")
        except Exception as e:
            logger.error(f"Error occurred: {e}")
            self.display_message(f"Error: {e}\n")

    def display_message(self, message):
        """Display a message in the chat area."""
        self.text_area.config(state='normal')  # Enable editing temporarily
        self.text_area.insert(END, message)
        self.text_area.config(state='disabled')  # Disable editing

        # Automatically scroll to the latest message
        self.text_area.yview(END)

if __name__ == "__main__":
    root = Tk()
    app = ClientBridgeGUI(root)
    root.mainloop()
