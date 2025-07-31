import anthropic
import os
from dotenv import load_dotenv
from rich import print
from typing import Type, Optional, List, Dict
from phantom.tool import BaseTool
import json

load_dotenv()


class Anthropic:
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

    def __init__(
            self,
            messages: list[dict[str, str]] = [],
            model: str = "claude-sonnet-4-20250514",
            temperature: float = 0.0,
            system_prompt: str | None = None,
            max_tokens: int = 2048,
            tools: Optional[List[BaseTool]] = None,
            verbose: bool = False,
            api_key: str | None = None
    ) -> None:
        """
        Initialize the LLM

        Parameters
        ----------
        messages : list[dict[str, str]], optional
            The list of messages, by default []
        model : str, optional
            The model to use, by default "claude-3-opus-20240229"
        temperature : float, optional
            The temperature to use, by default 0.0
        system_prompt : str, optional
            The system prompt to use, by default None
        max_tokens : int, optional
            The max tokens to use, by default 2048
        tools : list[BaseTool], optional
            The list of tools to use, by default None
        verbose : bool, optional
            The verbose to use, by default False
        api_key : str|None, optional
            The api key to use, by default None
        """
        self.api_key = api_key
        if self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
        else:
            if os.getenv("ANTHROPIC_API_KEY"):
                self.client = anthropic.Anthropic(
                    api_key=os.getenv("ANTHROPIC_API_KEY"))
            else:
                raise ValueError(
                    "No API key provided. Please provide an API key either through:\n"
                    "1. The api_key parameter\n"
                    "2. ANTHROPIC_API_KEY environment variable"
                )

        self.messages = messages
        self.model = model
        self.temperature = temperature
        self.system_prompt = system_prompt
        self.max_tokens = max_tokens
        self.tools = {tool.name: tool for tool in tools} if tools else {}
        self.verbose = verbose

        # Note: Anthropic uses 'system' for system prompt, which is handled differently
        # than a message. We pass it directly to the API on `run`.

    def run(self, prompt: str, save_messages: bool = True) -> str:
        """
        Run the LLM with support for tool calling.

        Parameters
        ----------
        prompt : str
            The prompt to run
        save_messages : bool
            Whether to save the conversation history

        Returns
        -------
        str
            The final response from the LLM
        """
        if save_messages:
            self.add_message(self.USER, prompt)

        tool_schemas = [tool.get_schema() for tool in self.tools.values()] if self.tools else []

        # First API call
        response = self.client.messages.create(
            model=self.model,
            system=self.system_prompt if self.system_prompt else "",
            messages=self.messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            tools=tool_schemas if tool_schemas else None,
        )

        if save_messages:
            # Append the assistant's initial response (which could be a tool call or text)
            self.messages.append(response.model_dump()['content'][0])


        # Check if the model wants to use a tool
        if response.stop_reason == "tool_use":
            tool_results = []
            for content_block in response.content:
                if content_block.type == "tool_use":
                    tool_name = content_block.name
                    tool_input = content_block.input
                    tool_id = content_block.id
                    if self.verbose:
                        print(f"Tool call: {tool_name} with input {tool_input}")

                    if tool_name in self.tools:
                        tool = self.tools[tool_name]
                        # Execute the tool and get the result
                        tool_run_result = tool.run(**tool_input)
                        # Handle the result properly - it's already a dict
                        if isinstance(tool_run_result, dict):
                            content = str(tool_run_result)
                        else:
                            content = str(tool_run_result)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": content,
                        })
                    else:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": f"Error: Tool '{tool_name}' not found.",
                            "is_error": True,
                        })
            
            # Add tool results to the conversation history
            if save_messages:
                self.messages.append({"role": self.USER, "content": tool_results})

            # Second API call to get a natural language response based on tool results
            final_response = self.client.messages.create(
                model=self.model,
                system=self.system_prompt if self.system_prompt else "",
                messages=self.messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            
            final_text = "".join([c.text for c in final_response.content if c.type == 'text'])
            if save_messages:
                self.add_message(self.ASSISTANT, final_text)

            return final_text
        
        # If no tool was used, return the text content
        final_text = "".join([c.text for c in response.content if c.type == 'text'])
        return final_text


    def add_message(self, role: str, content: str) -> None:
        """
        Add a message to the list of messages

        Parameters
        ----------
        role : str
            The role of the message
        content : str
            The content of the message
        """
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
        """
        Reset the messages and system prompt.
        """
        self.messages = []
        self.system_prompt = None