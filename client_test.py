import os
import asyncio
from dotenv import load_dotenv
from client_bridge.config import BridgeConfig, LLMConfig
from client_bridge.bridge import BridgeManager
from server.browser_navigator_server import BrowserNavigationServer
from loguru import logger


async def main():
    # Load environment variables
    load_dotenv()

    # Configure bridge
    server = BrowserNavigationServer()
    config = BridgeConfig(
        mcp=server,
        llm_config=LLMConfig(
            azure_endpoint=os.getenv("AZURE_OPEN_AI_ENDPOINT"),
            api_version=os.getenv("AZURE_OPEN_AI_API_VERSION"),
            api_key=os.getenv("AZURE_OPEN_AI_API_KEY"),
            deploy_name=os.getenv("AZURE_OPEN_AI_DEPLOYMENT_MODEL")
        ),
        system_prompt="You are a helpful assistant that can use tools to help answer questions."
    )
    
    logger.info(f"Starting bridge with model: {config.llm_config.deploy_name}")
    
    # Use bridge with context manager
    async with BridgeManager(config) as bridge:
        while True:
            try:
                user_input = input("\nEnter your prompt (or 'quit' to exit): ")
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                    
                response = await bridge.process_message(user_input)
                print(f"\nResponse: {response}")
                
            except KeyboardInterrupt:
                logger.info("\nExiting...")
                break
            except Exception as e:
                logger.error(f"\nError occurred: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")