from typing import Annotated, Any, Dict, List, Optional, Callable
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.base import BaseCheckpointSaver
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from sidekick_tools import playwright_tools, other_tools
from llm_invocation import invoke_with_retry_sync, LLMInvocationError
import uuid
import asyncio
from datetime import datetime
import logging
from playwright.async_api import Browser, Playwright

load_dotenv(override=True)

logger = logging.getLogger(__name__)


class State(TypedDict):
    messages: Annotated[List[Any], add_messages]
    success_criteria: str
    feedback_on_work: Optional[str]
    success_criteria_met: bool
    user_input_needed: bool


class EvaluatorOutput(BaseModel):
    feedback: str = Field(description="Feedback on the assistant's response")
    success_criteria_met: bool = Field(description="Whether the success criteria have been met")
    user_input_needed: bool = Field(
        description="True if more input is needed from the user, or clarifications, or the assistant is stuck"
    )


class Sidekick:
    """AI agent orchestrator using LangGraph state machine.

    Manages worker/tools/evaluator flow for completing tasks with tool-calling LLMs.
    Handles browser lifecycle, tool binding, and state management.
    """

    def __init__(self) -> None:
        """Initialize Sidekick instance with empty state."""
        self.worker_llm_with_tools: Optional[Any] = None
        self.evaluator_llm_with_output: Optional[Any] = None
        self.tools: Optional[List[BaseTool]] = None
        self.llm_with_tools: Optional[Any] = None
        self.graph: Optional[Any] = None  # CompiledStateGraph from langgraph
        self.sidekick_id: str = str(uuid.uuid4())
        self.memory: BaseCheckpointSaver = MemorySaver()
        self.browser: Optional[Browser] = None
        self.playwright: Optional[Playwright] = None

    async def setup(self) -> None:
        """Initialize LLMs, tools, and build state graph.

        Loads Playwright browser, binds tools to worker LLM, and compiles LangGraph.
        Must be called before any task execution.

        Raises:
            Exception: If Playwright launch or LLM initialization fails.
        """
        self.tools, self.browser, self.playwright = await playwright_tools()
        self.tools += await other_tools()
        worker_llm: ChatOpenAI = ChatOpenAI(model="gpt-4o-mini")
        self.worker_llm_with_tools = worker_llm.bind_tools(self.tools)
        evaluator_llm: ChatOpenAI = ChatOpenAI(model="gpt-4o-mini")
        self.evaluator_llm_with_output = evaluator_llm.with_structured_output(EvaluatorOutput)
        await self.build_graph()

    def worker(self, state: State) -> Dict[str, Any]:
        """Execute worker node to invoke LLM and process messages.

        This method invokes the worker LLM with tool binding to generate responses.
        It includes comprehensive error handling and retry logic for API failures.

        Args:
            state: Current graph state containing messages and context

        Returns:
            Updated state with LLM response

        Raises:
            LLMInvocationError: If LLM invocation fails after retries
        """
        system_message = f"""You are a helpful assistant that can use tools to complete tasks.
    You keep working on a task until either you have a question or clarification for the user, or the success criteria is met.
    You have many tools to help you, including tools to browse the internet, navigating and retrieving web pages.
    You have a tool to run python code, but note that you would need to include a print() statement if you wanted to receive output.
    The current date and time is {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    This is the success criteria:
    {state["success_criteria"]}
    You should reply either with a question for the user about this assignment, or with your final response.
    If you have a question for the user, you need to reply by clearly stating your question. An example might be:

    Question: please clarify whether you want a summary or a detailed answer

    If you've finished, reply with the final answer, and don't ask a question; simply reply with the answer.
    """

        if state.get("feedback_on_work"):
            system_message += f"""
    Previously you thought you completed the assignment, but your reply was rejected because the success criteria was not met.
    Here is the feedback on why this was rejected:
    {state["feedback_on_work"]}
    With this feedback, please continue the assignment, ensuring that you meet the success criteria or have a question for the user."""

        # Add in the system message

        found_system_message = False
        messages = state["messages"]
        for message in messages:
            if isinstance(message, SystemMessage):
                message.content = system_message
                found_system_message = True

        if not found_system_message:
            messages = [SystemMessage(content=system_message)] + messages

        # Invoke the LLM with tools with retry logic
        try:
            response = invoke_with_retry_sync(
                lambda: self.worker_llm_with_tools.invoke(messages),
                max_retries=3,
                initial_delay=1.0,
                operation_name="Worker LLM invocation"
            )
        except LLMInvocationError as e:
            logger.error(
                f"Worker LLM invocation failed: {e}",
                exc_info=True
            )
            # Return an error message to the user instead of crashing
            error_response = HumanMessage(
                content=f"I encountered an error while processing your request: {type(e.original_error).__name__}. "
                        f"Please try again or rephrase your request. Details: {str(e.original_error)}"
            )
            return {
                "messages": [error_response],
            }

        # Return updated state
        return {
            "messages": [response],
        }

    def worker_router(self, state: State) -> str:
        """Route worker output to tools or evaluator based on tool calls.

        Args:
            state: Current graph state with messages

        Returns:
            "tools" if last message has tool calls, else "evaluator"
        """
        last_message: BaseMessage = state["messages"][-1]

        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        else:
            return "evaluator"

    def format_conversation(self, messages: List[BaseMessage]) -> str:
        """Format conversation history for evaluator input.

        Args:
            messages: List of LangChain BaseMessage objects

        Returns:
            Formatted conversation string with User/Assistant labels
        """
        conversation: str = "Conversation history:\n\n"
        for message in messages:
            if isinstance(message, HumanMessage):
                conversation += f"User: {message.content}\n"
            elif isinstance(message, AIMessage):
                text: str = message.content or "[Tools use]"
                conversation += f"Assistant: {text}\n"
        return conversation

    def evaluator(self, state: State) -> Dict[str, Any]:
        """Evaluate the assistant's response against success criteria.

        This method invokes the evaluator LLM to determine if the task has been
        completed successfully. It includes comprehensive error handling and retry
        logic for API failures.

        Args:
            state: Current graph state with messages and criteria

        Returns:
            Updated state dictionary with evaluation results

        Raises:
            LLMInvocationError: If evaluator LLM invocation fails after retries
        """
        last_response: str = state["messages"][-1].content

        system_message: str = """You are an evaluator that determines if a task has been completed successfully by an Assistant.
    Assess the Assistant's last response based on the given criteria. Respond with your feedback, and with your decision on whether the success criteria has been met,
    and whether more input is needed from the user."""

        user_message: str = f"""You are evaluating a conversation between the User and Assistant. You decide what action to take based on the last response from the Assistant.

    The entire conversation with the assistant, with the user's original request and all replies, is:
    {self.format_conversation(state["messages"])}

    The success criteria for this assignment is:
    {state["success_criteria"]}

    And the final response from the Assistant that you are evaluating is:
    {last_response}

    Respond with your feedback, and decide if the success criteria is met by this response.
    Also, decide if more user input is required, either because the assistant has a question, needs clarification, or seems to be stuck and unable to answer without help.

    The Assistant has access to a tool to write files. If the Assistant says they have written a file, then you can assume they have done so.
    Overall you should give the Assistant the benefit of the doubt if they say they've done something. But you should reject if you feel that more work should go into this.

    """
        if state["feedback_on_work"]:
            user_message += f"Also, note that in a prior attempt from the Assistant, you provided this feedback: {state['feedback_on_work']}\n"
            user_message += "If you're seeing the Assistant repeating the same mistakes, then consider responding that user input is required."

        evaluator_messages: List[BaseMessage] = [
            SystemMessage(content=system_message),
            HumanMessage(content=user_message),
        ]

        # Invoke evaluator LLM with retry logic
        try:
            eval_result: EvaluatorOutput = invoke_with_retry_sync(
                lambda: self.evaluator_llm_with_output.invoke(evaluator_messages),
                max_retries=3,
                initial_delay=1.0,
                operation_name="Evaluator LLM invocation"
            )
        except LLMInvocationError as e:
            logger.error(
                f"Evaluator LLM invocation failed: {e}",
                exc_info=True
            )
            # Return a state that requests user input (fail-safe)
            new_state: Dict[str, Any] = {
                "messages": [
                    {
                        "role": "assistant",
                        "content": f"Evaluator encountered an error: {type(e.original_error).__name__}. "
                                   f"Requesting user input to proceed.",
                    }
                ],
                "feedback_on_work": f"Evaluation failed: {type(e.original_error).__name__}. Please try again.",
                "success_criteria_met": False,
                "user_input_needed": True,
            }
            return new_state

        new_state: Dict[str, Any] = {
            "messages": [
                {
                    "role": "assistant",
                    "content": f"Evaluator Feedback on this answer: {eval_result.feedback}",
                }
            ],
            "feedback_on_work": eval_result.feedback,
            "success_criteria_met": eval_result.success_criteria_met,
            "user_input_needed": eval_result.user_input_needed,
        }
        return new_state

    def route_based_on_evaluation(self, state: State) -> str:
        """Route evaluator output to end or back to worker.

        Args:
            state: Current graph state with evaluation results

        Returns:
            "END" if criteria met or user input needed, else "worker"
        """
        if state["success_criteria_met"] or state["user_input_needed"]:
            return "END"
        else:
            return "worker"

    async def build_graph(self) -> None:
        """Build LangGraph state machine for task execution.

        Creates nodes for worker (LLM), tools (tool execution), and evaluator (task validation).
        Compiles with memory checkpointer for state persistence.

        Raises:
            Exception: If graph compilation fails.
        """
        # Set up Graph Builder with State
        graph_builder: StateGraph = StateGraph(State)

        # Add nodes
        graph_builder.add_node("worker", self.worker)
        graph_builder.add_node("tools", ToolNode(tools=self.tools))
        graph_builder.add_node("evaluator", self.evaluator)

        # Add edges
        graph_builder.add_conditional_edges(
            "worker", self.worker_router, {"tools": "tools", "evaluator": "evaluator"}
        )
        graph_builder.add_edge("tools", "worker")
        graph_builder.add_conditional_edges(
            "evaluator", self.route_based_on_evaluation, {"worker": "worker", "END": END}
        )
        graph_builder.add_edge(START, "worker")

        # Compile the graph
        self.graph = graph_builder.compile(checkpointer=self.memory)

    async def run_superstep(
        self,
        message: str,
        success_criteria: Optional[str],
        history: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """Execute one conversation turn in the state machine.

        Invokes the LangGraph workflow with user message and success criteria,
        collects tool results, and returns updated conversation history.

        Args:
            message: User's task request
            success_criteria: Task completion criteria (optional, defaults to generic criteria)
            history: Previous conversation turns as list of role/content dicts

        Returns:
            Updated conversation history with user message, assistant response, and feedback
        """
        config: Dict[str, Any] = {"configurable": {"thread_id": self.sidekick_id}}

        state: Dict[str, Any] = {
            "messages": message,
            "success_criteria": success_criteria or "The answer should be clear and accurate",
            "feedback_on_work": None,
            "success_criteria_met": False,
            "user_input_needed": False,
        }
        result: Dict[str, Any] = await self.graph.ainvoke(state, config=config)
        user: Dict[str, str] = {"role": "user", "content": message}
        reply: Dict[str, str] = {"role": "assistant", "content": result["messages"][-2].content}
        feedback: Dict[str, str] = {"role": "assistant", "content": result["messages"][-1].content}
        return history + [user, reply, feedback]

    async def cleanup(self) -> None:
        """Properly cleanup browser and playwright resources.

        This method ensures that the browser and playwright instances are
        cleanly closed. It should be awaited to guarantee completion before
        the sidekick instance is destroyed.

        Raises:
            Exception: Any exceptions from browser.close() or playwright.stop()
                       are logged but not re-raised to prevent cleanup failures
                       from masking other errors.
        """
        if not self.browser:
            logger.debug(f"Sidekick {self.sidekick_id}: No browser to cleanup")
            return

        logger.info(f"Sidekick {self.sidekick_id}: Starting resource cleanup")

        # Close browser
        try:
            logger.debug(f"Sidekick {self.sidekick_id}: Closing browser")
            await self.browser.close()
            logger.info(f"Sidekick {self.sidekick_id}: Browser closed successfully")
        except Exception as e:
            logger.error(
                f"Sidekick {self.sidekick_id}: Failed to close browser: "
                f"{type(e).__name__}: {e}",
                exc_info=True
            )

        # Stop playwright
        if self.playwright:
            try:
                logger.debug(f"Sidekick {self.sidekick_id}: Stopping playwright")
                await self.playwright.stop()
                logger.info(f"Sidekick {self.sidekick_id}: Playwright stopped successfully")
            except Exception as e:
                logger.error(
                    f"Sidekick {self.sidekick_id}: Failed to stop playwright: "
                    f"{type(e).__name__}: {e}",
                    exc_info=True
                )

        logger.info(f"Sidekick {self.sidekick_id}: Cleanup completed")
