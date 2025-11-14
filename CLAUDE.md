# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ⚡ Experimental Project Mode

**This is an experimental research project.** You are encouraged to:
- ✅ Make autonomous decisions without asking for confirmation
- ✅ Implement improvements and enhancements proactively
- ✅ Refactor code to improve quality and maintainability
- ✅ Add tests, documentation, and type hints
- ✅ Optimize performance and reduce technical debt
- ✅ Merge branches and push code automatically

**Override these defaults ONLY if explicitly stated.** For example:
- "Code must pass all unit tests before committing"
- "Ask before removing features"
- "Wait for approval before deploying"

**Default behavior:** Proceed with confidence. You have full autonomy to make decisions you believe improve the project.

## Project Overview

**Sidekick** is an AI agent framework built on LangGraph that automates tasks through intelligent tool use. It combines an LLM worker (for task planning and execution), automated tool execution, and an evaluator (for success validation) in a closed-loop agentic workflow.

**Purpose**: Execute complex, multi-step tasks by leveraging web browsing, search, file I/O, code execution, and other tools while maintaining task-focused reasoning.

**Core Tech Stack**:
- **LangGraph**: State machine orchestration for deterministic, traceable execution
- **LangChain**: LLM integration and tool abstraction
- **OpenAI GPT-4o-mini**: Primary language model
- **Playwright**: Browser automation (headless off for debugging)
- **Gradio**: Web UI for task submission and feedback
- **Python 3.13.2**: Runtime environment

## Architecture Overview

### State Machine Flow

```
User Request (message + success_criteria)
    ↓
[WORKER] → Generate response or identify needed tools
    ↓
    ├─→ [TOOLS] → Execute all tool calls → [WORKER] (feedback loop)
    └─→ [EVALUATOR] → Assess if success_criteria met
           ↓
        ├─→ SUCCESS/USER_INPUT_NEEDED → END
        └─→ NOT MET → [WORKER] (with feedback) → repeat
```

### Key Components

1. **Sidekick Class** (`src/sidekick.py:36-223`):
   - Orchestrates the state machine using LangGraph
   - Manages browser lifecycle and tool initialization
   - Handles state persistence via MemorySaver (in-memory checkpointing)
   - `worker()`: LLM invocation with tools, injects success criteria and feedback
   - `evaluator()`: Structured output validation against success criteria
   - `run_superstep()`: Entry point for single conversation turn

2. **State Definition** (`src/sidekick.py:20-25`):
   ```python
   State: messages, success_criteria, feedback_on_work, success_criteria_met, user_input_needed
   ```
   - `messages`: LangChain message list (with automatic reducer via `add_messages`)
   - `success_criteria`: User-specified goal for task validation
   - `feedback_on_work`: Evaluator feedback injected back to worker for refinement
   - Boolean flags track completion and escalation

3. **Tool Integration** (`src/sidekick_tools.py`):
   - **Playwright Tools**: Page navigation, content fetching, element interaction (form filling, clicking)
   - **File Management**: Read/write/delete in `sandbox/` directory (isolated)
   - **Web Search**: Google Serper API integration
   - **Wikipedia**: Knowledge queries
   - **Python REPL**: Arbitrary code execution with print output capture
   - **Push Notifications**: Pushover API (user alerts)
   - Tools are auto-converted to OpenAI function-calling format via LangChain's `bind_tools()`

4. **UI Layer** (`src/app.py`):
   - Gradio-based chat interface
   - State lifecycle: `setup()` → `process_message()` → optional `reset()`
   - Cleanup on session termination (browser/playwright teardown)

## Common Development Tasks

### Setup & Environment

```bash
# Install dependencies (uses UV package manager)
uv sync

# Create/update .env with required API keys
# Required: OPENAI_API_KEY, SERPER_API_KEY (optional: PUSHOVER_TOKEN, PUSHOVER_USER)
cp .env.example .env
# Edit .env with your credentials
```

### Running the Application

```bash
# Start the Gradio web UI (auto-opens in browser)
python src/app.py

# The UI runs on http://localhost:7860
```

### Development & Testing

```bash
# Run type checking (when mypy is added)
mypy src/

# Run tests (when test suite is added)
pytest tests/

# Run a single test
pytest tests/test_sidekick.py::test_worker_invocation
```

### Key Development Patterns

1. **Adding a New Tool**:
   - Define function in `sidekick_tools.py`
   - Wrap with `Tool()` or use LangChain toolkit (e.g., `FileManagementToolkit`)
   - Return from `other_tools()` or `playwright_tools()`
   - Automatically picked up by `bind_tools()` in `Sidekick.setup()`

2. **Modifying Success Criteria Logic**:
   - Edit `Sidekick.evaluator()` system/user prompts (lines 122-151)
   - Adjust `EvaluatorOutput` Pydantic model if new decision logic needed
   - Evaluator is synchronous; consider async refactoring for large context

3. **Customizing Worker Behavior**:
   - Edit `Sidekick.worker()` system prompt (lines 58-79)
   - Inject date/time via `datetime.now().strftime()`
   - Feedback mechanism: `state["feedback_on_work"]` guides refinement loops

4. **Browser Configuration**:
   - Headless mode toggle: `src/sidekick_tools.py:23` (`headless=False` for debugging)
   - Set `headless=True` for production/CI
   - Browser persisted in `Sidekick.browser`; cleanup in `cleanup()`

## Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| **LangGraph over LangChain Agent** | Explicit control flow, state transparency, easier debugging |
| **MemorySaver (in-memory)** | Fast prototyping; persistence requires DB layer |
| **Structured Output (Evaluator)** | Deterministic decision routing; prevents ambiguous LLM outputs |
| **Playwright (async)** | Non-blocking browser control; better resource efficiency |
| **GPT-4o-mini (hardcoded)** | Cost/latency tradeoff; should be configurable |
| **Sandbox directory isolation** | Safety; prevents file operations outside `sandbox/` |
| **Headless=False** | Observability during debugging; switch to `True` for production |

## Known Limitations & Future Improvements

### Security Concerns
- `.env` file exposes secrets (add to gitignore; rotate keys)
- Python REPL tool allows arbitrary code execution (restrict in production)
- File operations can potentially escape sandbox with path traversal

### Performance
- Browser created per Sidekick instance (resource-heavy); consider pooling
- Message history grows unbounded (implement sliding window or summarization)
- No caching for repeated searches/queries
- Evaluator synchronous; could be async

### Missing Features
- No persistence layer (state lost on restart)
- Minimal error handling; tool failures crash silently
- No logging framework (only print statements)
- All settings hardcoded (model, timeouts, API endpoints)
- No input validation (message length, success criteria format)
- No test suite

### UI/UX Gaps
- No file upload/download
- Limited conversation history management
- No tool execution visualization
- Basic error messages to user

## File Structure Reference

```
src/
  sidekick.py          # Core state machine (Sidekick class, State, EvaluatorOutput)
  app.py               # Gradio UI and lifecycle management
  sidekick_tools.py    # Tool definitions and registry
sandbox/               # Isolated directory for file operations
.env                   # API keys (NEVER commit; add to .gitignore)
pyproject.toml         # Dependencies (managed via UV)
uv.lock                # Locked dependency versions
main.py                # Stub entry point (not actively used)
README.md              # Basic project description
```

## Environment Variables

**Required**:
- `OPENAI_API_KEY`: OpenAI API key for GPT-4o-mini

**Optional**:
- `SERPER_API_KEY`: Google Serper API for web search (required for search tool functionality)
- `PUSHOVER_TOKEN`: Pushover app token for notifications
- `PUSHOVER_USER`: Pushover user key for notifications
- `LANGSMITH_API_KEY`: LangSmith tracing (if enabled)

## Decision-Making Guidelines

### Autonomous Decision Framework

You have full autonomy to make these decisions **without asking**:

1. **Code Quality**: Refactor, add type hints, improve naming, optimize algorithms
2. **Testing**: Add tests, improve test coverage, fix failing tests
3. **Documentation**: Add docstrings, comments, README updates, architecture diagrams
4. **Dependencies**: Add well-vetted dependencies if they improve the codebase
5. **Error Handling**: Add try-catch blocks, improve error messages, add validation
6. **Performance**: Optimize hot paths, reduce technical debt, improve efficiency
7. **Git Operations**: Commit, push, merge, delete branches as needed
8. **File Organization**: Move files, rename modules, reorganize directories
9. **Feature Completion**: Complete partially-implemented features, fill in TODOs
10. **Breaking Changes**: Only if they improve maintainability (this is experimental)

### When to Ask for Confirmation

Explicitly ask ONLY if:
- The user provides a constraint like "code must pass all tests before committing"
- The user says "wait for approval before deploying"
- The change removes functionality the user may depend on
- The change requires choices between multiple valid approaches

## Important Notes for Future Work

1. **Security**: Rotate API keys immediately; `.env` should never be in version control
2. **Async/Await**: Most operations are async; always use `await` when calling `setup()` and `run_superstep()`
3. **State Machine**: LangGraph thread_id ties conversations to a Sidekick instance; `reset()` creates new instance
4. **Tool Binding**: Tools auto-discovered via `bind_tools()`; order matters for function-calling preference
5. **Feedback Loop**: Evaluator feedback injected via `feedback_on_work` state variable; enables iterative refinement
6. **Resource Cleanup**: Always call `sidekick.cleanup()` to close browser/playwright or pass `sidekick` to Gradio state with `delete_callback`

## Code Quality Standards

When making improvements, aim for:

- **Type Hints**: All functions should have complete type annotations
- **Docstrings**: All public functions/classes should have comprehensive docstrings
- **Error Handling**: Specific exceptions caught, not generic `Exception`
- **Testing**: New code should have unit tests with >80% coverage
- **Logging**: Use structured logging, avoid print statements
- **No Duplication**: Extract common patterns into reusable functions
- **Performance**: Reasonable time/space complexity for the task
- **Security**: Validate inputs, sanitize outputs, avoid hardcoded secrets

## Experimental Features

This project is actively evolving. Feel free to:
- Experiment with new patterns or approaches
- Try out new libraries or frameworks
- Refactor legacy code
- Remove deprecated code
- Propose architectural improvements
- Add metrics or observability

Just ensure each change is:
1. ✅ Well-tested (new tests added)
2. ✅ Well-documented (docstrings, comments)
3. ✅ All existing tests still pass
4. ✅ Committed with clear commit messages
