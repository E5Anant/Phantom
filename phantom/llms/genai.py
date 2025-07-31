import os
from dotenv import load_dotenv
from typing import List, Dict, Optional
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold, FunctionDeclaration, Tool
from phantom.tool import BaseTool
import json

load_dotenv()

class Gemini:
    USER = "user"
    MODEL = "model"
    TOOL = "tool" # Role for function/tool responses

    def __init__(self,
                 messages: list[dict[str, str]] = [],
                 model: str = "gemini-2.5-flash-lite", # A more powerful model is recommended for complex tool use
                 temperature: float = 0.7,
                 system_prompt: str | None = None,
                 max_tokens: int = 8192,
                 tools: Optional[List[BaseTool]] = None,
                 verbose: bool = False,
                 safety_settings: list = [],
                 api_key: str | None = None
                 ):
        self.safety_settings = safety_settings or [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "No API key provided. Please provide an API key either through the 'api_key' parameter or the 'GEMINI_API_KEY' environment variable."
            )
        genai.configure(api_key=self.api_key)

        self.messages = list(messages)
        self.model = model
        self.temperature = temperature
        self.system_prompt = system_prompt
        self.max_tokens = max_tokens
        self.tools = {tool.name: tool for tool in tools} if tools else {}
        self.verbose = verbose
        
        generation_config = {
            "temperature": self.temperature,
            "max_output_tokens": self.max_tokens,
        }
        
        # Correctly prepare tools for the Gemini API
        self.gemini_tools = [Tool(function_declarations=[FunctionDeclaration(**tool.get_schema())]) for tool in self.tools.values()] if self.tools else None

        self.client = genai.GenerativeModel(
            model_name=self.model,
            safety_settings=self.safety_settings,
            generation_config=generation_config,
            system_instruction=self.system_prompt,
        )

    def _execute_tool_call(self, tool_name: str, tool_args: Dict):
        """Executes a single tool call synchronously."""
        if self.verbose:
            print(f"  - Executing tool: {tool_name} with args: {tool_args}")
        
        if tool_name in self.tools:
            tool_instance = self.tools[tool_name]
            try:
                # The tool's run method should return a dictionary
                result = tool_instance.run(**tool_args)
                if self.verbose:
                    print(f"  - Tool '{tool_name}' result: {result}")
                # The result passed back to the model should be the direct output of the tool
                return result 
            except Exception as e:
                error_message = f"Error executing tool {tool_name}: {e}"
                if self.verbose:
                    print(f"  - [ERROR] {error_message}")
                return {"success": False, "error_message": error_message}
        else:
            return {"success": False, "error_message": f"Tool '{tool_name}' not found."}

    def _handle_function_calls(self, function_calls: List) -> List[Dict]:
        """Handles multiple function calls sequentially."""
        tool_outputs = []
        for call in function_calls:
            tool_name = call.name
            tool_args = dict(call.args)
            tool_output = self._execute_tool_call(tool_name, tool_args)
            tool_outputs.append({
                "tool_call": call,
                "output": tool_output
            })
        return tool_outputs

    def run(self, prompt: str, save_messages: bool = True) -> str:
        """
        Runs a multi-turn conversation with the Gemini model, handling tool calls
        in a loop until a final text response is generated.
        """
        history = self.messages if save_messages else []

        if self.system_prompt and not any(m.get('role') == 'system' for m in history):
             pass

        history.append({"role": self.USER, "parts": [{"text": prompt}]})

        while True:
            try:
                response = self.client.generate_content(history, tools=self.gemini_tools)
                
                # Check if response has candidates
                if not response.candidates:
                    return "No response generated."
                
                candidate = response.candidates[0]
                
                # Check for function calls in the response
                function_calls = []
                if hasattr(candidate, 'content') and candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, 'function_call') and part.function_call:
                            function_calls.append(part.function_call)

                if not function_calls:
                    # No function calls, return the text response
                    final_text = response.text if response.text else "No text response generated."
                    if save_messages:
                        # Add the model's final response to the history
                        history.append({"role": self.MODEL, "parts": [{"text": final_text}]})
                        self.messages = history
                    if self.verbose:
                        print(f"Final response: {final_text}")
                    return final_text

                if self.verbose:
                    print(f"Model wants to call {len(function_calls)} tool(s)...")

                # Add the model's request to use a tool to the history
                history.append({"role": self.MODEL, "parts": candidate.content.parts})

                # Execute the function calls
                tool_results = []
                for fc in function_calls:
                    result = self._execute_tool_call(fc.name, dict(fc.args))
                    tool_results.append(result)

                # Add the tool's response to the history
                tool_response_parts = []
                for fc, result in zip(function_calls, tool_results):
                    # Ensure result is properly formatted for the API
                    if isinstance(result, str):
                        # If result is a string, wrap it in a simple structure
                        formatted_result = {"output": result}
                    elif isinstance(result, dict):
                        # If it's already a dict, use it as is
                        formatted_result = result
                    else:
                        # For any other type, convert to string
                        formatted_result = {"output": str(result)}
                    
                    tool_response_parts.append({
                        "function_response": {
                            "name": fc.name,
                            "response": formatted_result,
                        }
                    })

                history.append({
                    "role": self.TOOL,
                    "parts": tool_response_parts
                })

            except Exception as e:
                if self.verbose:
                    print(f"Error in run method: {e}")
                return f"An error occurred: {e}"


    def add_message(self, role: str, content: str) -> None:
        """Adds a message to the conversation history."""
        self.messages.append({"role": role, "parts": [{"text": content}]})

    def reset(self) -> None:
        """Resets the conversation history."""
        self.messages = []