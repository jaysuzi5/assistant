import gradio as gr
from sidekick import Sidekick
import asyncio
import logging
from typing import List, Dict, Tuple, Optional, Any
from logging_config import setup_logging, LogLevel

# Initialize logging framework
_logging_config = setup_logging(log_level=LogLevel.INFO)
logger = logging.getLogger(__name__)


async def setup() -> Sidekick:
    """Initialize Sidekick instance with LLM setup and browser launch.

    Called when Gradio UI loads to create a new agent session.

    Returns:
        Initialized Sidekick instance ready for task execution.
    """
    sidekick: Sidekick = Sidekick()
    await sidekick.setup()
    return sidekick


async def process_message(
    sidekick: Sidekick,
    message: str,
    success_criteria: Optional[str],
    history: List[Dict[str, str]]
) -> Tuple[List[Dict[str, str]], Sidekick]:
    """Process user message through the Sidekick workflow.

    Executes one conversation turn and returns updated history.

    Args:
        sidekick: Current Sidekick instance
        message: User's task request
        success_criteria: Task completion criteria (optional)
        history: Previous conversation turns

    Returns:
        Tuple of (updated conversation history, sidekick instance)
    """
    results: List[Dict[str, str]] = await sidekick.run_superstep(message, success_criteria, history)
    return results, sidekick


async def reset() -> Tuple[str, str, None, Sidekick]:
    """Reset conversation and create new Sidekick instance.

    Clears message/criteria fields and initializes fresh agent session.

    Returns:
        Tuple of (empty message, empty criteria, None for history, new Sidekick)
    """
    new_sidekick: Sidekick = Sidekick()
    await new_sidekick.setup()
    return "", "", None, new_sidekick


def free_resources(sidekick: Optional[Sidekick]) -> None:
    """Cleanup callback for Gradio state deletion.

    This callback is invoked by Gradio when a session state is deleted (e.g., when
    the user closes the browser or the session times out). Since Gradio callbacks
    are synchronous but our cleanup is async, we use asyncio.run() to properly
    await the async cleanup.

    Args:
        sidekick: The Sidekick instance to cleanup, or None if already cleaned.
    """
    if not sidekick:
        logger.debug("No Sidekick instance to cleanup")
        return

    logger.info(f"free_resources called for Sidekick {sidekick.sidekick_id}")

    try:
        # Gradio state deletion callback is synchronous, so we need to run
        # the async cleanup in a new event loop.
        asyncio.run(sidekick.cleanup())
        logger.info(f"Sidekick {sidekick.sidekick_id} cleanup completed successfully")
    except Exception as e:
        logger.error(
            f"Exception during cleanup of Sidekick {sidekick.sidekick_id}: "
            f"{type(e).__name__}: {e}",
            exc_info=True
        )


with gr.Blocks(title="Sidekick", theme=gr.themes.Default(primary_hue="emerald")) as ui:
    gr.Markdown("## Sidekick Personal Co-Worker")
    sidekick = gr.State(delete_callback=free_resources)

    with gr.Row():
        chatbot = gr.Chatbot(label="Sidekick", height=300, type="messages")
    with gr.Group():
        with gr.Row():
            message = gr.Textbox(show_label=False, placeholder="Your request to the Sidekick")
        with gr.Row():
            success_criteria = gr.Textbox(
                show_label=False, placeholder="What are your success critiera?"
            )
    with gr.Row():
        reset_button = gr.Button("Reset", variant="stop")
        go_button = gr.Button("Go!", variant="primary")

    ui.load(setup, [], [sidekick])
    message.submit(
        process_message, [sidekick, message, success_criteria, chatbot], [chatbot, sidekick]
    )
    success_criteria.submit(
        process_message, [sidekick, message, success_criteria, chatbot], [chatbot, sidekick]
    )
    go_button.click(
        process_message, [sidekick, message, success_criteria, chatbot], [chatbot, sidekick]
    )
    reset_button.click(reset, [], [message, success_criteria, chatbot, sidekick])


ui.launch(inbrowser=True)
