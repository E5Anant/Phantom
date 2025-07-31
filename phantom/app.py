from phantom.llms import GroqLLM, Openai, Gemini, Anthropic
from phantom.codesmith import CodesmithTool
from phantom.func import WebSearchTool, Orgotool
import asyncio

import asyncio
from rich.console import Console
from rich.panel import Panel
from rich.columns import Columns
from rich.layout import Layout
from rich.text import Text
import orgo
from os import environ
from dotenv import load_dotenv
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gui_agents.s2.agents.agent_s import AgentS2

load_dotenv()
import pyfiglet
pyfiglet.print_figlet("Phantom", font="starwars", colors="cyan", width=90)

class PhantomAssistant:
    def __init__(self,
                 llm:Openai=None,
                 tools=None
                ):
        """
        Initialize a Phantom Assistant instance with user's LLM and system prompt.
        
        Args:
            llm: Any LLM instance (OpenAI, Gemini, Anthropic, Groq, etc.)
            tools: List of tools to provide to the LLM
        """
        # Load the system prompt
        try:
            with open("phantom/prompts/base.md", mode="r", encoding="utf-8") as f:
                system_prompt = f.read()
        except UnicodeDecodeError:
            # Fallback to different encoding if utf-8 fails
            with open("phantom/prompts/base.md", mode="r", encoding="latin-1") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            # Fallback system prompt if file not found
            system_prompt = (
                "You are Phantom, a highly advanced AI agent with powerful tools. "
                "Use your tools to accomplish any task with maximum efficiency and accuracy."
            )
        
        # Store the user's LLM and apply our system prompt
        if llm is None:
            # Default to GroqLLM if no LLM provided
            self.llm = GroqLLM(
                system_prompt=system_prompt,
                tools=tools or []
            )
        else:
            # Get the LLM class and create a new instance with our system prompt
            llm_class = type(llm)
            
            # Extract current LLM parameters
            llm_params = {}
            if hasattr(llm, 'api_key'):
                llm_params['api_key'] = llm.api_key
            if hasattr(llm, 'model'):
                llm_params['model'] = llm.model
            if hasattr(llm, 'max_tokens'):
                llm_params['max_tokens'] = llm.max_tokens
            if hasattr(llm, 'temperature'):
                llm_params['temperature'] = llm.temperature
                
            # Create new instance with our system prompt and user's parameters
            self.llm = llm_class(
                system_prompt=system_prompt,
                tools=tools or [],
                **llm_params
            )
                
        self.console = Console()

    def main(self):
        """
        Main method to run the Phantom Assistant.
        """
        
        # Welcome message
        self.console.print(Panel("[bold cyan]Welcome to Phantom Assistant![/bold cyan]",
                            subtitle="Type 'exit' or 'quit' to end."))

        # Main interactive loop
        while True:
            try:
                user_input = self.console.input("\n[bold magenta]You:[/bold magenta] ")
                if user_input.lower() in ('exit', 'quit'):
                    self.console.print("[bold cyan]Goodbye![/bold cyan]")
                    break

                if not user_input:
                    continue

                # Let the user's LLM handle the input with our system prompt
                response = self.llm.run(user_input)

                self.console.print(Panel(response, title="[bold green]Assistant[/bold green]", border_style="green"))

            except Exception as e:
                self.console.print(f"[bold red]An error occurred: {e}[/bold red]")
                # Reset the LLM's message history to start fresh
                if hasattr(self.llm, 'reset'):
                    self.llm.reset()


def main():
    """
    Main function to set up and run the Phantom Assistant with user's choice of LLM.
    """
    # Create Computer and tools
    Computer = orgo.Computer(
        api_key=environ.get('ORGO_API_KEY', "your_api_key_here"), 
        project_id='computer-1fwkokg'
    )
    
    internal_llm = Gemini()  # Using Gemini as the internal LLM for CodesmithTool
    
    # Create tools list
    tools = [
        CodesmithTool(llm_instance=internal_llm), 
        WebSearchTool(), 
        Orgotool(Computer=Computer)
    ]
    
    # Example: User can choose any LLM they want
    # User's OpenAI LLM:
    # user_llm = Openai(api_key="user_openai_key", model="gpt-4")
    
    # User's Gemini LLM:
    # user_llm = Gemini(api_key="user_gemini_key")
    
    # User's Anthropic LLM:
    # user_llm = Anthropic(api_key="user_anthropic_key", model="claude-3-sonnet")
    
    # For this example, we'll use GroqLLM but user can pass any LLM
    user_llm = GroqLLM()  # User's choice of LLM
    
    # Create PhantomAssistant with user's LLM and tools
    # The system prompt from base.md will be automatically applied
    assistant = PhantomAssistant(
        llm=user_llm,
        tools=tools
    )
    
    # Run the assistant
    assistant.main()


def main_with_agents():
    """
    Alternative main function with AgentS2 and user's choice of LLM.
    """
    # Create Computer and AgentS2 instances
    Computer = orgo.Computer(
        api_key=environ.get('ORGO_API_KEY', "your_api_key_here"), 
        project_id='computer-1fwkokg'
    )
    
    # Create AgentS2 instance for advanced GUI automation
    from gui_agents.s2.agents.agent_s import AgentS2
    from gui_agents.s2.agents.grounding import OSWorldACI
    
    engine_params = {"engine_type": "openai", "model": "gpt-4o"}
    grounding_params = {"engine_type": "anthropic", "model": "claude-3-sonnet"}
    
    grounding_agent = OSWorldACI(
        platform="windows",
        engine_params_for_generation=engine_params,
        engine_params_for_grounding=grounding_params
    )
    
    agent_s2 = AgentS2(
        engine_params=engine_params,
        grounding_agent=grounding_agent,
        platform="windows",
        action_space="pyautogui",
        observation_type="screenshot"
    )
    
    internal_llm = Gemini()
    
    # Create tools with AgentS2-enabled Orgotool
    tools = [
        CodesmithTool(llm_instance=internal_llm), 
        WebSearchTool(), 
        Orgotool(Computer=Computer, agent=agent_s2)
    ]
    
    # User can choose their LLM here:
    # user_llm = Openai(api_key="user_openai_key", model="gpt-4")
    # user_llm = Gemini(api_key="user_gemini_key")
    # user_llm = Anthropic(api_key="user_anthropic_key", model="claude-3-sonnet")
    
    user_llm = GroqLLM()  # Default example - user can replace with any LLM
    
    # Create PhantomAssistant instance with user's LLM
    # The system prompt from base.md will be automatically applied
    assistant = PhantomAssistant(
        llm=user_llm,
        tools=tools
    )
    
    # Run the assistant
    assistant.main()


if __name__ == "__main__":
    # You can choose which main function to run:
    main()              # Simple setup like main.py - basic Orgotool
    # main_with_agents()  # Advanced setup with AgentS2 capabilities