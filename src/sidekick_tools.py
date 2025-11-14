from playwright.async_api import async_playwright
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


load_dotenv(override=True)

logger = logging.getLogger(__name__)

# Configuration for optional Python REPL tool
ENABLE_PYTHON_REPL = os.getenv("ENABLE_PYTHON_REPL", "false").lower() == "true"

pushover_token = os.getenv("PUSHOVER_TOKEN")
pushover_user = os.getenv("PUSHOVER_USER")
pushover_url = "https://api.pushover.net/1/messages.json"
serper = GoogleSerperAPIWrapper()

if ENABLE_PYTHON_REPL:
    logger.warning("⚠️  Python REPL tool is ENABLED. This allows arbitrary code execution.")
    logger.warning("⚠️  Only enable this in trusted environments with trusted agents.")

async def playwright_tools():
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=browser)
    return toolkit.get_tools(), browser, playwright


def push(text: str):
    """Send a push notification to the user"""
    requests.post(pushover_url, data = {"token": pushover_token, "user": pushover_user, "message": text})
    return "success"


def get_file_tools():
    toolkit = FileManagementToolkit(root_dir="sandbox")
    return toolkit.get_tools()


async def other_tools():
    """Load available tools, conditionally including Python REPL based on ENABLE_PYTHON_REPL env var.

    Tools loaded:
    - File management (always available)
    - Push notifications (always available)
    - Web search (always available)
    - Wikipedia (always available)
    - Python REPL (only if ENABLE_PYTHON_REPL=true)

    Returns:
        list: List of available tools
    """
    push_tool = Tool(
        name="send_push_notification",
        func=push,
        description="Use this tool when you want to send a push notification"
    )
    file_tools = get_file_tools()

    tool_search = Tool(
        name="search",
        func=serper.run,
        description="Use this tool when you want to get the results of an online web search"
    )

    wikipedia = WikipediaAPIWrapper()
    wiki_tool = WikipediaQueryRun(api_wrapper=wikipedia)

    # Build list of tools
    tools = file_tools + [push_tool, tool_search, wiki_tool]

    # Conditionally add Python REPL tool
    if ENABLE_PYTHON_REPL:
        logger.info("Adding Python REPL tool to available tools")
        python_repl = PythonREPLTool()
        tools.append(python_repl)
        logger.debug(f"Available tools: {[t.name if hasattr(t, 'name') else str(t) for t in tools]}")
    else:
        logger.debug("Python REPL tool is disabled (ENABLE_PYTHON_REPL=false)")
        logger.debug(f"Available tools: {[t.name if hasattr(t, 'name') else str(t) for t in tools]}")

    return tools

