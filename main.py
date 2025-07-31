from phantom.app import PhantomAssistant
from phantom.llms import Gemini, GroqLLM, Openai, Anthropic

from phantom.codesmith import CodesmithTool
from phantom.func import WebSearchTool, Orgotool, ReadFileTool
from gui_agents.s2.agents.agent_s import AgentS2
from gui_agents.s2.agents.grounding import OSWorldACI
from orgo import Computer

from os import environ
from dotenv import load_dotenv
load_dotenv()

engine_params = {"engine_type": "gemini", "model": "gemini-2.5-flash-lite"}
grounding_params = {"engine_type": "gemini", "model": "gemini-2.5-flash-lite"}

grounding_agent = OSWorldACI(
    platform='windows',
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
# Create Computer instance
codesmith_tool = CodesmithTool(llm_instance=Gemini()) # Make Sure to get your api key in .env file with GEMINI_API_KEY
websearchtool = WebSearchTool()
read_file_tool = ReadFileTool()  # Assuming ReadFileTool is defined in automation.py
orgotool = Orgotool(Computer=Computer(api_key=environ.get('ORGO_API_KEY', "your_api_key_here")), agent=agent_s2)
tools = [codesmith_tool, websearchtool, orgotool, read_file_tool]
llm = Gemini('gemini-2.0-flash-lite-001')


def main():
    """
    Main function to run Phantom Assistant with basic Orgotool.
    """

    PhantomAssistant(llm=llm, tools=tools).main()


if __name__ == "__main__":
    main()