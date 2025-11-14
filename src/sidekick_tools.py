from playwright.async_api import async_playwright, Browser, Playwright
from langchain_community.agent_toolkits import PlayWrightBrowserToolkit
from dotenv import load_dotenv
import os
import requests
import logging
from langchain_community.tools import Tool
from langchain_community.agent_toolkits import FileManagementToolkit
from langchain_community.tools.wikipedia.tool import WikipediaQueryRun
from langchain_experimental.tools import PythonREPLTool
from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain_community.utilities.wikipedia import WikipediaAPIWrapper
from langchain_core.tools import BaseTool
from typing import List, Tuple, Optional
from config import PUSHOVER_REQUEST_TIMEOUT


load_dotenv(override=True)

logger = logging.getLogger(__name__)

# Configuration for optional Python REPL tool
ENABLE_PYTHON_REPL: bool = os.getenv("ENABLE_PYTHON_REPL", "false").lower() == "true"

pushover_token: Optional[str] = os.getenv("PUSHOVER_TOKEN")
pushover_user: Optional[str] = os.getenv("PUSHOVER_USER")
pushover_url: str = "https://api.pushover.net/1/messages.json"
serper: GoogleSerperAPIWrapper = GoogleSerperAPIWrapper()

if ENABLE_PYTHON_REPL:
    logger.warning("⚠️  Python REPL tool is ENABLED. This allows arbitrary code execution.")
    logger.warning("⚠️  Only enable this in trusted environments with trusted agents.")

async def playwright_tools() -> Tuple[List[BaseTool], Browser, Playwright]:
    """Launch Playwright browser and return web browsing tools.

    Returns:
        Tuple of (list of browser tools, Browser instance, Playwright instance)

    Raises:
        Exception: If Playwright launch fails.
    """
    playwright: Playwright = await async_playwright().start()
    browser: Browser = await playwright.chromium.launch(headless=False)
    toolkit: PlayWrightBrowserToolkit = PlayWrightBrowserToolkit.from_browser(async_browser=browser)
    return toolkit.get_tools(), browser, playwright


def push(text: str) -> str:
    """Send a push notification to the user.

    Args:
        text: Message content to send

    Returns:
        "success" if notification sent, otherwise error message

    Raises:
        requests.exceptions.Timeout: If the request times out
        requests.exceptions.RequestException: If the request fails
    """
    try:
        requests.post(
            pushover_url,
            data={
                "token": pushover_token,
                "user": pushover_user,
                "message": text
            },
            timeout=PUSHOVER_REQUEST_TIMEOUT
        )
        return "success"
    except requests.exceptions.Timeout:
        logger.error(
            f"Push notification timeout after {PUSHOVER_REQUEST_TIMEOUT}s"
        )
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Push notification failed: {e}")
        raise


def get_file_tools() -> List[BaseTool]:
    """Load file management tools from LangChain toolkit.

    Returns:
        List of file manipulation tools (read, write, delete in sandbox/)
    """
    toolkit: FileManagementToolkit = FileManagementToolkit(root_dir="sandbox")
    return toolkit.get_tools()


async def other_tools() -> List[BaseTool]:
    """Load available tools, conditionally including Python REPL based on ENABLE_PYTHON_REPL env var.

    Tools loaded:
    - File management (always available)
    - Push notifications (always available)
    - Web search (always available)
    - Wikipedia (always available)
    - Python REPL (only if ENABLE_PYTHON_REPL=true)

    Returns:
        List of available tools
    """
    push_tool: Tool = Tool(
        name="send_push_notification",
        func=push,
        description="Use this tool when you want to send a push notification"
    )
    file_tools: List[BaseTool] = get_file_tools()

    tool_search: Tool = Tool(
        name="search",
        func=serper.run,
        description="Use this tool when you want to get the results of an online web search"
    )

    wikipedia: WikipediaAPIWrapper = WikipediaAPIWrapper()
    wiki_tool: WikipediaQueryRun = WikipediaQueryRun(api_wrapper=wikipedia)

    # Build list of tools
    tools: List[BaseTool] = file_tools + [push_tool, tool_search, wiki_tool]

    # Conditionally add Python REPL tool
    if ENABLE_PYTHON_REPL:
        logger.info("Adding Python REPL tool to available tools")
        python_repl: PythonREPLTool = PythonREPLTool()
        tools.append(python_repl)
        logger.debug(f"Available tools: {[t.name if hasattr(t, 'name') else str(t) for t in tools]}")
    else:
        logger.debug("Python REPL tool is disabled (ENABLE_PYTHON_REPL=false)")
        logger.debug(f"Available tools: {[t.name if hasattr(t, 'name') else str(t) for t in tools]}")

    return tools

