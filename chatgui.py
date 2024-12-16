import asyncio
import os
from tkinter import (
    Tk,
    Text,
    Button,
    Scrollbar,
    VERTICAL,
    RIGHT,
    Y,
    END,
    Frame,
    PhotoImage,
)
from dotenv import load_dotenv
from client_bridge.config import BridgeConfig
from client_bridge.bridge import BridgeManager
from client_bridge.llm_config import get_default_llm_config
from server.browser_navigator_server import BrowserNavigationServer
from loguru import logger
import threading

# Load environment variables
load_dotenv()


class ClientBridgeGUI:
    def __init__(self, master):
        self.master: Tk = master
        self.master.title("Client Bridge GUI")

        # Set application icon
        icon_path = os.path.join(os.getcwd(), "doc", "globe_icon.png")
        icon_image = PhotoImage(file=icon_path)
        self.master.iconphoto(False, icon_image)

        # Frame for the text area and scrollbar
        self.chat_frame = Frame(master)
        self.chat_frame.pack(padx=10, pady=10, fill="both", expand=True)

        # Set up the text area for chat history (readonly)
        self.text_area = Text(
            self.chat_frame, wrap="word", height=20, width=50, state="disabled"
        )
        self.text_area.pack(side="left", fill="both", expand=True)

        # Create a tag for response text with specific color
        self.text_area.tag_configure("response", foreground="#3377ff")

        # Scrollbar for the text area
        self.scrollbar = Scrollbar(
            self.chat_frame, command=self.text_area.yview, orient=VERTICAL
        )
        self.scrollbar.pack(side=RIGHT, fill=Y)
        self.text_area.config(yscrollcommand=self.scrollbar.set)

        # Frame for the user input and button
        self.input_frame = Frame(master)
        self.input_frame.pack(padx=10, pady=10, fill="x")

        # Text widget for the user input (editable)
        self.user_input = Text(self.input_frame, height=3, wrap="word", width=50)
        self.user_input.pack(side="left", fill="x", expand=True)

        # Send button
        self.send_button = Button(
            self.input_frame, text="Send", command=self.process_input
        )
        self.send_button.pack(side="right")

        # Set up configuration for server and bridge
        self.server = BrowserNavigationServer()
        self.config = BridgeConfig(
            mcp=self.server,
            llm_config=get_default_llm_config(),
            system_prompt="You are a helpful assistant that can use tools to help answer questions.",
        )

        logger.info(f"Starting bridge with model: {self.config.llm_config.deploy_name}")

        # Initialize the asyncio event loop in a separate thread
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.start_event_loop, daemon=True).start()

        # Initialize the bridge asynchronously
        asyncio.run_coroutine_threadsafe(self.initialize_bridge(), self.loop)

    def start_event_loop(self):
        """Start the asyncio event loop."""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

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

            # Run the asynchronous input handler in the event loop
            asyncio.run_coroutine_threadsafe(self.handle_input(user_input), self.loop)

    async def handle_input(self, user_input):
        """Handle user input asynchronously and display response."""
        try:
            response = await self.process_message(user_input)
            # Schedule the UI update in the main thread
            self.master.after(0, self.display_response, f"Response: {response}\n")
        except Exception as e:
            logger.error(f"Error occurred: {e}")
            self.master.after(0, self.display_message, f"Error: {e}\n")

    def display_message(self, message):
        """Display a message in the chat area."""
        self.text_area.config(state="normal")  # Enable editing temporarily
        self.text_area.insert(END, message)
        self.text_area.config(state="disabled")  # Disable editing

        # Automatically scroll to the latest message
        self.text_area.yview(END)

    def display_response(self, message):
        """Display a response message in the chat area with specific color."""
        self.text_area.config(state="normal")  # Enable editing temporarily
        self.text_area.insert(END, message, "response")
        self.text_area.config(state="disabled")  # Disable editing

        # Automatically scroll to the latest message
        self.text_area.yview(END)


if __name__ == "__main__":
    root = Tk()
    app = ClientBridgeGUI(root)
    root.mainloop()
