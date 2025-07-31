from openai import OpenAI as OpenAIClient
import os
from dotenv import load_dotenv
from rich import print
from typing import Optional, List
from phantom.tool import BaseTool
import json

load_dotenv()


class Openai:
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"

    def __init__(self,
                 messages: list[dict[str, str]] = [],
                 model: str = "gpt-4.1-2025-04-14",
                 temperature: float = 0.0,
                 system_prompt: str | None = None,
                 max_tokens: int = 2048,
                 tools: Optional[List[BaseTool]] = None,
                 verbose: bool = False,
                 api_key: str | None = None
                 ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "No API key provided. Please provide an API key either through the 'api_key' parameter or the 'OPENAI_API_KEY' environment variable."
            )

        self.client = OpenAIClient(api_key=self.api_key)
        self.messages = messages
        self.model = model
        self.temperature = temperature
        self.system_prompt = system_prompt
        self.max_tokens = max_tokens
        self.tools = {tool.name: tool for tool in tools} if tools else {}
        self.verbose = verbose

        if self.system_prompt is not None and not any(m['role'] == self.SYSTEM for m in self.messages):
            self.add_message(self.SYSTEM, self.system_prompt)

    def run(self, prompt: str, save_messages: bool = True) -> str:
        """
        Run the LLM with support for tool calling.
        """
        if save_messages:
            self.add_message(self.USER, prompt)

        # Convert BaseTool schemas to OpenAI's expected format
        tool_schemas = [{"type": "function", "function": tool.get_schema()} for tool in self.tools.values()] if self.tools else None
        
        # First API call
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            tools=tool_schemas,
            tool_choice="auto" if self.tools else None,
        )
        
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        # Check if the model decided to call a tool
        if tool_calls:
            if save_messages:
                self.messages.append(response_message)  # Save assistant's reply with tool calls

            # Execute all tool calls
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                if self.verbose:
                    print(f"Tool call: {function_name} with args {function_args}")
                
                if function_name in self.tools:
                    tool = self.tools[function_name]
                    # Execute the tool
                    tool_result = tool.run(**function_args)
                    
                    if save_messages:
                        # Add tool result to message history
                        # Handle the result properly - it's already a dict
                        if isinstance(tool_result, dict):
                            content = json.dumps(tool_result)
                        else:
                            content = str(tool_result)
                        self.messages.append({
                            "tool_call_id": tool_call.id,
                            "role": self.TOOL,
                            "name": function_name,
                            "content": content,
                        })
                else:
                     if self.verbose:
                        print(f"Error: Tool '{function_name}' not found.")

            # Second API call to get the final natural language response
            second_response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            final_text = second_response.choices[0].message.content
            if save_messages:
                self.add_message(self.ASSISTANT, final_text)
            return final_text
        
        # If no tool call, just return the content
        final_text = response_message.content
        if save_messages:
            self.add_message(self.ASSISTANT, final_text)
        return final_text


    def add_message(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})

    def __getitem__(self, index) -> dict[str, str] | list[dict[str, str]]:
        if isinstance(index, slice):
            return self.messages[index]
        elif isinstance(index, int):
            return self.messages[index]
        else:
            raise TypeError("Invalid argument type")

    def __setitem__(self, index, value) -> None:
        if isinstance(index, slice):
            self.messages[index] = value
        elif isinstance(index, int):
            self.messages[index] = value
        else:
            raise TypeError("Invalid argument type")

    def reset(self) -> None:
        """Resets the conversation history and system prompt."""
        self.messages = []
        if self.system_prompt:
            self.add_message(self.SYSTEM, self.system_prompt)