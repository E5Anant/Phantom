import requests
from pywhatkit import search
from AppOpener import close, open as appopen
from webbrowser import open as webopen
from bs4 import BeautifulSoup
from rich import print
import webbrowser
from duckduckgo_search import DDGS
from googlesearch import search as netsearch
from phantom.tool import BaseTool, Field, ToolParameterType
import os
import PyPDF2
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36'

def open_top_n(query: str, n: int = 1):
    for url in netsearch(query, num_results=n):
        print("Opening:", url)
        webbrowser.open_new_tab(url)

def get_directory_structure(root_dir=None):
    """
    Returns the structure of the current working directory (or given root_dir) as a nested dict.
    Ignores folders such as .venv and __pycache__.
    """
    if root_dir is None:
        root_dir = os.getcwd()
    dir_structure = {}
    ignore_dirs = {'.venv', '__pycache__'}

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Remove ignored directories in-place so os.walk doesn't descend into them
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs]
        rel_path = os.path.relpath(dirpath, root_dir)
        parent = dir_structure
        if rel_path != ".":
            for part in rel_path.split(os.sep):
                parent = parent.setdefault(part, {})
        parent['__files__'] = filenames

    return dir_structure

def read_file(filepath: str):
    """
    Reads the content of a file based on its extension.
    Supports: txt, py, js, csv, pdf, and more.
    Returns the content as a string.
    """
    ext = os.path.splitext(filepath)[1].lower()
    if ext in ['.txt', '.py', '.js', '.csv', '.md', '.json', '.html', '.css']:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    elif ext == '.pdf':
        try:
            content = ""
            with open(filepath, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    content += page.extract_text() or ""
            return content
        except ImportError:
            return "PyPDF2 is required to read PDF files."
        except Exception as e:
            return f"Error reading PDF: {e}"
    else:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Cannot read file: {e}"

class ReadFileTool(BaseTool):
    def __init__(self):
        self.name="ReadFileTool"
        self.description="Reads the content of a file and returns it as a string."
        self.parameters=[
            Field(
                name="file_path",
                description="Path to the file to read.",
                required=True,
                field_type=ToolParameterType.STRING
            )
        ]
        super().__init__()
        
    def _run(self, file_path: str):
        return read_file(file_path)

def google_search(query: str):
    search(query)
    return True

class OpenAppTool():
    def __init__(self):
        pass
    def _run(self, apps:list):
        return self.open_app(apps)
    def open_app(self, apps:list, sess=requests.session()):
        """
        Attempts to open an application.  First tries using AppOpener.
        If that fails, it attempts to find the app's website via Google search 
        and opens it in the browser.  If the website search also fails, it defaults 
        to a generic Google search for the app name.
        """
        for app in apps:
            try:
                print(appopen(app, match_closest=True, output=True, throw_error=True))
            except Exception as e:
                print(f"AppOpener failed: {e}")  # Print the exception for debugging

                try:
                    open_top_n(app)
                except Exception as e2:
                    print(f"Website search and fallback failed: {e2}")
                    print(f"Falling back to generic Google search for {app}")
                    google_search(app)  # As a last resort

        return "Successfully opened apps"
    
def youtube_search(prompt):
    url4search = f"https://www.youtube.com/results?search_query={prompt}"
    webopen(url4search)
    return True

def web_search(self, query: str, max_results: int = 3):
    """Execute web search with multiple fallback methods."""
    if not query or not isinstance(query, str):
        return {"success": False, "error_message": "Query must be a non-empty string"}
    
    if max_results < 1 or max_results > 10:
        max_results = 3
        logger.warning(f"max_results clamped to {max_results}")
    
    output = ""
    search_successful = False
    
    # Method 1: Try Google Search first
    try:
        logger.info(f"Searching via Google for: {query}")
        results = list(netsearch(query, advanced=True, num_results=max_results))
        
        if results:
            logger.info(f"Google search returned {len(results)} results")
            output += "=== Google Search Results ===\n\n"
            for i, result in enumerate(results):
                output += f"{i+1}. \nTitle: {result.title}\n"
                output += f"Description: {result.description}\n"
                output += f"Source: {result.url}\n\n"
            search_successful = True
        else:
            logger.warning("Google search returned no results")
            
    except Exception as e:
        logger.error(f"Google search failed: {str(e)}")
    
    # Method 2: Fallback to DuckDuckGo if Google fails
    if not search_successful:
        try:
            logger.info(f"Trying DuckDuckGo search for: {query}")
            ddg = DDGS()
            ddg_results = ddg.text(query, max_results=max_results)
            
            if ddg_results:
                logger.info(f"DuckDuckGo search returned {len(ddg_results)} results")
                output += "=== DuckDuckGo Search Results ===\n\n"
                for i, result in enumerate(ddg_results):
                    output += f"{i+1}. \nTitle: {result.get('title', 'No Title')}\n"
                    output += f"Body: {result.get('body', 'No Description')}\n"
                    output += f"Source: {result.get('href', 'No URL')}\n\n"
                search_successful = True
            else:
                logger.warning("DuckDuckGo search returned no results")
                
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {str(e)}")
    
    if not search_successful:
        return {"success": False, "error_message": f"All search methods failed for query: {query}"}
    
    return {"success": True, "results": output.strip()}
    
class CloseAppTool():
    def __init__(self):
        pass
    def _run(self, apps:list):
        return self.close_app(apps)
    def close_app(self, apps:list):
        for app in apps:
            if "chrome" in app:
                print("Chrome can't be closed due to speech recognition software")
            try:
                print(close(app, match_closest=True, output=True, throw_error=True))
            except Exception:
                return f"Failed to close {app}"

        return "Successfully closed apps"