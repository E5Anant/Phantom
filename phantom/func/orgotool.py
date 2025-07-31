from phantom.tool import BaseTool, Field, ToolParameterType
from typing import Dict, Any, Optional, List
import orgo
import dotenv
from os import getenv
import os
import io
import sys
import time
import pyautogui
from gui_agents.s2.agents.agent_s import AgentS2
from gui_agents.s2.agents.grounding import OSWorldACI
dotenv.load_dotenv()

CONFIG = {
    "model": os.getenv("AGENT_MODEL", "gpt-4o"),
    "model_type": os.getenv("AGENT_MODEL_TYPE", "openai"),
    "grounding_model": os.getenv("GROUNDING_MODEL", "claude-3-7-sonnet-20250219"),
    "grounding_type": os.getenv("GROUNDING_MODEL_TYPE", "anthropic"),
    "max_steps": int(os.getenv("MAX_STEPS", "10")),
    "step_delay": float(os.getenv("STEP_DELAY", "0.5")),
    "remote": os.getenv("USE_CLOUD_ENVIRONMENT", "false").lower() == "true"
}


class LocalExecutor:
    def __init__(self):
        self.pyautogui = pyautogui
        if sys.platform == "win32":
            self.platform = "windows"
        elif sys.platform == "darwin":
            self.platform = "darwin"
        else:
            self.platform = "linux"
    
    def screenshot(self):
        img = self.pyautogui.screenshot()
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer.getvalue()
    
    def exec(self, code):
        exec(code, {"pyautogui": self.pyautogui, "time": time})
    
    def destroy(self):
        # No cleanup needed for local executor
        pass


class RemoteExecutor:
    def __init__(self):
        self.computer = orgo.Computer()
        self.platform = "linux"
    
    def screenshot(self):
        return self.computer.screenshot_base64()
    
    def exec(self, code):
        result = self.computer.exec(code)
        if not result['success']:
            raise Exception(result.get('error', 'Execution failed'))
        if result['output']:
            print(f"Output: {result['output']}")
    
    def destroy(self):
        self.computer.destroy()


class Orgotool(BaseTool):
    """
    This tool uses OrgoAI to perform various tasks such as browser controling and even multi mouse clicking process and gives a llm access to a remote virtual computer which can do various tasks such as web browsing and web scraping, file management, and more all in a Ubuntu OS Environment.
    """

    def __init__(self, 
                 agent: AgentS2,
                 api_key: Optional[str] = None, 
                 Computer: Optional[orgo.Computer] = None,
                 ):
        """Args:
        - api_key (str, optional): The API key for authenticating with OrgoAI (defaults to ORGO_API_KEY env var).
        - Computer (orgo.Computer, optional): Pre-initialized Computer instance.
        - agent (AgentS2, optional): Pre-configured AgentS2 instance for advanced GUI automation.
        """
        self.name = "orgotool"
        self.description = "Use OrgoAI to perform tasks on a remote virtual computer. This tool can control a web browser (for web scrapping and more tasks), manage files, and execute commands in a Ubuntu OS environment."
        self.params = [
            Field(
                name="prompt",
                description="The task to perform using OrgoAI.",
                required=True,
                field_type=ToolParameterType.STRING
            )
        ]
        
        # Set the agent instance
        self.agent = agent
        
        super().__init__()
        if not api_key:
            api_key = getenv("ORGO_API_KEY")
            if Computer:
                self.computer = Computer
            else:
                self.computer = orgo.Computer(api_key=api_key)
        else:
            self.computer = orgo.Computer(api_key=api_key)
    
    def run_task(self, executor, instruction):
        """Run a task using the agent and executor."""
        if not self.agent:
            raise ValueError("No AgentS2 instance provided. Please provide an agent parameter during initialization.")
        
        print(f"\n🤖 Task: {instruction}")
        print(f"📍 Mode: {'Remote' if isinstance(executor, RemoteExecutor) else 'Local'}\n")
        
        # Get max_steps from agent if available, otherwise use default
        max_steps = getattr(self.agent, 'max_steps', int(os.getenv("MAX_STEPS", "10")))
        step_delay = float(os.getenv("STEP_DELAY", "0.5"))
        
        results = []
        for step in range(max_steps):
            print(f"Step {step + 1}/{max_steps}")
            
            obs = {"screenshot": executor.screenshot()}
            info, action = self.agent.predict(instruction=instruction, observation=obs)
            
            if info:
                print(f"💭 {info}")
                results.append(f"Info: {info}")
            
            if not action or not action[0]:
                print("✅ Complete")
                results.append("Task completed successfully")
                return {"success": True, "results": results}
            
            try:
                print(f"🔧 {action[0]}")
                executor.exec(action[0])
                results.append(f"Action: {action[0]}")
            except Exception as e:
                print(f"❌ Error: {e}")
                results.append(f"Error: {e}")
                instruction = "The previous action failed. Try a different approach."
            
            time.sleep(step_delay)
        
        print("⏱️ Max steps reached")
        results.append("Max steps reached")
        return {"success": False, "results": results, "error": "Max steps reached"}

    def _run(self, prompt: str) -> Dict[str, Any]:
        """Run the OrgoAI task with the provided prompt."""
        if not prompt or not isinstance(prompt, str):
            return {"success": False, "error_message": "Prompt must be a non-empty string"}
        
        try:
            # Check if we should use advanced agent mode (if prompt suggests GUI automation and agent is available)
            gui_keywords = ["click", "type", "screenshot", "automation", "gui", "interface", "browser control", "mouse", "keyboard"]
            use_agent_mode = self.agent is not None and any(keyword in prompt.lower() for keyword in gui_keywords)
            
            if use_agent_mode:
                # Use advanced agent mode with LocalExecutor or RemoteExecutor
                # Determine remote mode from environment or default to local
                remote = os.getenv("USE_CLOUD_ENVIRONMENT", "false").lower() == "true"
                executor = RemoteExecutor() if remote else LocalExecutor()
                try:
                    result = self.run_task(executor, prompt)
                    return {
                        "success": result["success"],
                        "result": result,
                        "metadata": {"prompt": prompt, "mode": "agent"}
                    }
                finally:
                    executor.destroy()
            else:
                # Use standard OrgoAI mode
                response = self.computer.prompt(prompt)
                return {
                    "success": True,
                    "result": response,
                    "metadata": {"prompt": prompt, "mode": "standard"}
                }
        except Exception as e:
            return {
                "success": False,
                "error_message": str(e),
                "metadata": {"prompt": prompt}
            }