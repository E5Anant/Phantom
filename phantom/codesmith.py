from os import environ, path
from dotenv import load_dotenv
from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.layout import Layout
from rich.columns import Columns
from rich.rule import Rule
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.theme import Theme
from time import time as t
from phantom.tool import BaseTool, Field, ToolParameterType
import re
import sys
import subprocess
from typing import Tuple, Union
import asyncio
import logging
import threading
import concurrent.futures
from functools import partial

# Load environment variables
load_dotenv()

# Initialize Rich console with Monokai theme
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "code": "#F8F8F2 on #272822",
    "thinking": "#B52EE2",
    "output": "#66D9EF",
    "prompt": "#F92672",
    "time": "#FD971F"
})
console = Console(theme=custom_theme)

# Load system prompt
prompt_path = path.join("phantom", "prompts", "codesmith.md")
with open(prompt_path, "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

# Additional guidance for automation imports
system_prompt_addition = """
IMPORTANT: When writing Python code to automate tasks, use these specific import paths:
- from phantom.func.automation import OpenAppTool, CloseAppTool, google_search, youtube_search, read_file
- DO NOT use paths like 'util.automation' or other incorrect paths

Example of correct code:
```python
from phantom.func.automation import OpenAppTool

def main():
    result = OpenAppTool()._run(["notepad", "Wordpad"])
    print(result)
    return "Opened notepad successfully"

if __name__ == "__main__":
    output = main()
    print(output)
```
Use this guidance strictly; avoid unnecessary loops when writing task automation scripts.
"""

# Combined system prompt
COMBINED_SYSTEM_PROMPT = SYSTEM_PROMPT + system_prompt_addition

# Import LLM interfaces
from .llms import GroqLLM, Openai, Gemini, Anthropic

class Codesmith:
    def __init__(self, llm_instance: Union[GroqLLM, Openai, Gemini, Anthropic]):
        """
        Initialize Codesmith with a pre-configured LLM instance.
        """
        self.system_prompt = COMBINED_SYSTEM_PROMPT
        self.llm = llm_instance
        # If LLM has init messages/settings, reinitialize messages
        self.llm.__init__(
            messages=llm_instance.messages if hasattr(llm_instance, 'messages') else None,
            model=llm_instance.model,
            temperature=llm_instance.temperature,
            max_tokens=llm_instance.max_tokens if hasattr(llm_instance, 'max_tokens') else None,
            system_prompt=self.system_prompt,
            api_key=llm_instance.api_key if hasattr(llm_instance, 'api_key') else None
        )

    def _execute_subprocess(self, script_file: str, description: str = "⚡ Executing code...") -> subprocess.CompletedProcess:
        """
        Execute subprocess in a thread-safe manner with progress indication.
        """
        def run_with_progress():
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console, transient=True) as progress:
                task = progress.add_task(description, total=None)
                result = subprocess.run([sys.executable, script_file], capture_output=True, text=True)
                progress.remove_task(task)
                return result
        
        # Use thread pool for faster execution
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_with_progress)
            return future.result()

    async def execute_code(self, response_text: str, retry_count: int = 0, max_retries: int = 2) -> Tuple[str, bool, bool]:
        """
        Execute Python code with error handling and automatic LLM retry on errors.
        Returns:
        - clean output text
        - success flag
        - continuation flag
        """
        # Extract and display thinking section if present
        think_match = re.search(r"<think>(.*?)</think>", response_text, re.DOTALL)
        if think_match:
            thinking_content = think_match.group(1).strip()
            console.print(Rule("🧠 AI Thinking Process", style="thinking"))
            console.print(Panel(thinking_content, title="Thought Process", style="thinking"))
            console.print()
        
        # Extract Python code from response
        code_match = re.search(r"```python(.*?)```", response_text, re.DOTALL)
        if not code_match:
            console.print("❌ No valid Python code found in response", style="error")
            return "", False, False

        code_block = code_match.group(1).strip()
        
        # Remove any <think> tags that might be inside the code block
        code_block = re.sub(r"<think>.*?</think>", "", code_block, flags=re.DOTALL).strip()
        
        # Skip if the code block is empty after cleaning
        if not code_block:
            console.print("❌ No executable Python code found after cleaning", style="error")
            return "", False, False
        
        retry_suffix = f" (Retry {retry_count})" if retry_count > 0 else ""
        console.print(Rule(f"🔧 Generated Code{retry_suffix}", style="thinking"))
        console.print(Panel(Syntax(code_block, "python", theme="monokai", line_numbers=True), title="Generated Code"))

        imports_snippet = (
            "import sys\n"
            "import os\n"
            "sys.path.insert(0, os.path.abspath('.'))\n"
            "from phantom.func.automation import OpenAppTool, CloseAppTool, google_search, youtube_search\n"
        )
        script = imports_snippet + "\n" + code_block
        script_file = "temp_codesmith.py"
        with open(script_file, "w", encoding="utf-8") as temp_file:
            temp_file.write(script)

        # Execute code using threaded subprocess for better performance
        result = self._execute_subprocess(script_file, "⚡ Executing code...")

        if result.returncode == 0:
            output = result.stdout.strip()
            needs_continue = "CONTINUE" in output
            clean_output = output.replace("CONTINUE", "").strip()
            console.print(Rule("✅ Execution Result", style="success"))
            if clean_output:
                console.print(Panel(clean_output, title="Output", style="output"))
            return clean_output, True, needs_continue
        else:
            stderr_output = result.stderr
            
            # Check if it's a module not found error first
            if "ModuleNotFoundError: No module named" in stderr_output:
                missing_module = self._extract_missing_module(stderr_output)
                if missing_module:
                    console.print(Rule("📦 Missing Module Detected", style="warning"))
                    console.print(f"[bold yellow]Missing module: {missing_module}[/bold yellow]")
                    
                    # Ask user if they want to install the module
                    user_choice = console.input(f"[bold cyan]Do you want to install '{missing_module}' using pip? (y/n): [/bold cyan]").strip().lower()
                    
                    if user_choice in ['y', 'yes']:
                        # Try to install the module
                        install_success = self._install_module(missing_module)
                        
                        if install_success:
                            console.print(f"[bold green]✅ Successfully installed '{missing_module}'[/bold green]")
                            console.print("[bold cyan]Retrying code execution...[/bold cyan]")
                            
                            # Retry execution with threading
                            retry_result = self._execute_subprocess(script_file, "⚡ Re-executing code...")
                            
                            if retry_result.returncode == 0:
                                output = retry_result.stdout.strip()
                                needs_continue = "CONTINUE" in output
                                clean_output = output.replace("CONTINUE", "").strip()
                                console.print(Rule("✅ Execution Result (After Install)", style="success"))
                                if clean_output:
                                    console.print(Panel(clean_output, title="Output", style="output"))
                                return clean_output, True, needs_continue
                            else:
                                stderr_output = retry_result.stderr  # Update error for potential LLM retry
                        else:
                            console.print(f"[bold red]❌ Failed to install '{missing_module}'[/bold red]")
                    else:
                        console.print("[bold yellow]Installation cancelled by user[/bold yellow]")
            
            # If we have retries left and it's not a simple module error, ask LLM to fix the code
            if retry_count < max_retries:
                console.print(Rule(f"🔄 Auto-fixing Code (Attempt {retry_count + 1}/{max_retries})", style="warning"))
                console.print(Panel(stderr_output, title="Error Details", style="error"))
                
                # Create error fixing prompt for the LLM
                error_fix_prompt = f"""
The following Python code resulted in an error. Please analyze the error and provide a corrected version:

**Original Code:**
```python
{code_block}
```

**Error Output:**
```
{stderr_output}
```

Please provide the corrected Python code that fixes this error. Make sure to:
1. Analyze what went wrong
2. Fix the specific issue causing the error
3. Maintain the original functionality
4. Return only the corrected Python code in a ```python``` block

<think>
Let me analyze this error and understand what went wrong...
</think>
"""
                
                console.print("[bold cyan]🤖 Asking AI to fix the error...[/bold cyan]")
                
                # Get LLM to fix the code using threading
                def get_fix_response():
                    return self.llm.run(error_fix_prompt)
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(get_fix_response)
                    fix_response = future.result()
                
                fix_response_text = fix_response if isinstance(fix_response, str) else str(fix_response)
                
                # Recursively call execute_code with the fixed response
                return await self.execute_code(fix_response_text, retry_count + 1, max_retries)
            
            # If all retries exhausted, return the final error
            console.print(Rule("❌ Execution Failed - Max Retries Reached", style="error"))
            console.print(Panel(stderr_output, title="Final Error Details", style="error"))
            return stderr_output, False, False

    def _extract_missing_module(self, error_output: str) -> str:
        """
        Extract the missing module name from ModuleNotFoundError.
        """
        import re
        # Look for pattern: ModuleNotFoundError: No module named 'module_name'
        match = re.search(r"ModuleNotFoundError: No module named ['\"]([^'\"]+)['\"]", error_output)
        if match:
            return match.group(1)
        return None

    def _install_module(self, module_name: str) -> bool:
        """
        Install a Python module using pip with threading for faster execution.
        Returns True if successful, False otherwise.
        """
        try:
            console.print(f"[bold cyan]Installing {module_name} using pip...[/bold cyan]")
            
            def install_with_progress():
                with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console, transient=True) as progress:
                    task = progress.add_task(f"Installing {module_name}...", total=None)
                    install_result = subprocess.run(
                        [sys.executable, "-m", "pip", "install", module_name],
                        capture_output=True,
                        text=True
                    )
                    progress.remove_task(task)
                    return install_result
            
            # Use thread pool for faster pip installation
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(install_with_progress)
                install_result = future.result()
            
            if install_result.returncode == 0:
                return True
            else:
                console.print(f"[bold red]Pip install failed:[/bold red]")
                console.print(Panel(install_result.stderr, title="Pip Error", style="error"))
                return False
                
        except Exception as e:
            console.print(f"[bold red]Error during installation: {e}[/bold red]")
            return False

    async def automator(self, prompt: str, verbose: bool = True) -> Tuple[str, bool]:
        """
        Handle prompt through LLM, execute code, and manage continuation with threading support.
        """
        console.print(Rule("AI Processing", style="thinking"))
        
        # Generate response and ensure string - use threading for LLM calls
        def get_llm_response():
            return self.llm.run(prompt)
        
        # Use thread pool for LLM execution to prevent blocking
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(get_llm_response)
            raw_response = future.result()
        
        response_text = raw_response if isinstance(raw_response, str) else str(raw_response)

        # Extract thinking section and display it
        think_match = re.search(r"<think>(.*?)</think>", response_text, re.DOTALL)
        # if think_match:
        #     thinking_content = think_match.group(1).strip()
        #     console.print("🧠 [bold thinking]AI Thinking Process:[/bold thinking]")
        #     console.print(f"[thinking]{thinking_content}[/thinking]")
        #     console.print()

        # Clean response by removing Python code blocks and think tags
        cleaned_response = re.sub(r"```python.*?```", "", response_text, flags=re.DOTALL)
        cleaned_response = re.sub(r"<think>.*?</think>", "", cleaned_response, flags=re.DOTALL).strip()
        
        if verbose and cleaned_response:
            console.print(Panel(cleaned_response, title="🤖 AI Response", style="thinking"))

        output, success, continue_flag = await self.execute_code(response_text)
        if continue_flag:
            return await self.automator(f"{output}\nCONTINUE", verbose)
        return output, success

    async def main(self):
        console.print(Panel(Text("🚀 Codesmith AI Assistant", style="bold magenta"), subtitle="Powered by Multi-LLM Architecture"))
        while True:
            prompt = console.input("[prompt]>>> [\x1b[0m")
            if prompt.lower() in ('exit', 'quit'):
                console.print("👋 Goodbye! Thanks for using Codesmith!", style="info")
                break
            output, success = await self.automator(prompt)
            console.print(Panel(f"Success: {success}\nOutput Length: {len(output)} chars", title="Summary"))

class CodesmithTool(BaseTool):
    def __init__(self, llm_instance: Union[GroqLLM, Openai, Gemini, Anthropic]):
        self.codesmith = Codesmith(llm_instance)
        self.name = "CodesmithTool"
        self.description = "A tool which generates python code for automating tasks like website making, opening and closing, working in cwd and more."
        self.params = [Field(name="prompt", field_type=ToolParameterType.STRING, description="The task prompt for automation.", required=True)]
        super().__init__()

    def run(self, prompt: str):
        """
        Synchronous run method that executes the async automator.
        This is called by the LLM's tool execution system.
        """
        try:
            # Use asyncio.run to execute the async method synchronously
            import asyncio
            try:
                # Check if an event loop is already running
                loop = asyncio.get_running_loop()
                # If so, we can't use asyncio.run, so we need a different approach
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.codesmith.automator(prompt, verbose=False))
                    output, success = future.result()
            except RuntimeError:
                # No event loop running, safe to use asyncio.run
                output, success = asyncio.run(self.codesmith.automator(prompt, verbose=False))
            
            return {"output": output, "success": success}
        except Exception as e:
            return {"output": f"Error executing codesmith: {e}", "success": False}

    async def _run(self, prompt: str):
        """
        Async version for backward compatibility.
        """
        output, success = await self.codesmith.automator(prompt, verbose=False)
        return {"output": output, "success": success}

if __name__ == "__main__":
    gemini_llm = Gemini(model="gemini-2.5-flash-lite-preview-06-17", temperature=1.0, max_tokens=2048)
    assistant = Codesmith(gemini_llm)
    asyncio.run(assistant.main())
