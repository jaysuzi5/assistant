# Technical Details: Type Hints Implementation

## Type Annotation Strategies

### 1. Concrete Types vs Generic Types

#### Before (Generic)
```python
# Too vague - what's in the dict? what type of list?
def worker(self, state: State) -> Dict:
    messages = state["messages"]  # Type of messages unknown
    # ...
    return {"messages": [...]}  # What's in the dict?
```

#### After (Specific)
```python
# Clear - Dict keys and value types are explicit
def worker(self, state: State) -> Dict[str, Any]:
    messages: List[BaseMessage] = state["messages"]
    # ...
    return {"messages": [response]}  # Return type explicit
```

### 2. Handling Complex Types

#### LangChain Message Types
```python
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage

# All message types inherit from BaseMessage
def format_conversation(self, messages: List[BaseMessage]) -> str:
    conversation: str = ""
    for message in messages:
        if isinstance(message, HumanMessage):
            conversation += f"User: {message.content}\n"
        elif isinstance(message, AIMessage):
            text: str = message.content or "[Tools use]"
            conversation += f"Assistant: {text}\n"
    return conversation
```

#### Playwright Types
```python
from playwright.async_api import Browser, Playwright

class Sidekick:
    def __init__(self) -> None:
        self.browser: Optional[Browser] = None
        self.playwright: Optional[Playwright] = None

    async def cleanup(self) -> None:
        if not self.browser:
            return

        try:
            await self.browser.close()
        except Exception as e:
            logger.error(f"Failed to close browser: {e}")

        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception as e:
                logger.error(f"Failed to stop playwright: {e}")
```

#### Tool Types
```python
from langchain_core.tools import BaseTool

def get_file_tools() -> List[BaseTool]:
    toolkit: FileManagementToolkit = FileManagementToolkit(root_dir="sandbox")
    return toolkit.get_tools()
```

### 3. Optional Types & None Handling

#### Pattern: Optional API Keys
```python
pushover_token: Optional[str] = os.getenv("PUSHOVER_TOKEN")
pushover_user: Optional[str] = os.getenv("PUSHOVER_USER")

# Usage: handle None case
if pushover_token and pushover_user:
    # Safe to use
    requests.post(pushover_url, data={"token": pushover_token, ...})
```

#### Pattern: Optional Method Arguments
```python
async def run_superstep(
    self,
    message: str,
    success_criteria: Optional[str],  # Can be None
    history: List[Dict[str, str]]
) -> List[Dict[str, str]]:
    # Default if None
    criteria = success_criteria or "The answer should be clear and accurate"
```

#### Pattern: Optional Attributes
```python
class Sidekick:
    def __init__(self) -> None:
        self.browser: Optional[Browser] = None  # Initially None
        self.playwright: Optional[Playwright] = None

    async def setup(self) -> None:
        # After setup, browser and playwright are assigned
        self.browser, _ = await playwright_tools()
```

### 4. Complex Return Types

#### Tuple Returns
```python
# Function returns a tuple of 3 elements
async def playwright_tools() -> Tuple[List[BaseTool], Browser, Playwright]:
    playwright: Playwright = await async_playwright().start()
    browser: Browser = await playwright.chromium.launch(headless=False)
    toolkit: PlayWrightBrowserToolkit = ...
    return toolkit.get_tools(), browser, playwright

# Usage: unpacking
tools, browser, playwright = await playwright_tools()
```

#### Gradio Callback Returns
```python
from typing import Tuple

async def reset() -> Tuple[str, str, None, Sidekick]:
    """Clear all inputs and reset state."""
    new_sidekick: Sidekick = Sidekick()
    await new_sidekick.setup()
    return "", "", None, new_sidekick  # (message, criteria, history, sidekick)
```

### 5. Pydantic Models & Structured Output

#### Model Definition
```python
from pydantic import BaseModel, Field

class EvaluatorOutput(BaseModel):
    feedback: str = Field(description="Feedback on the assistant's response")
    success_criteria_met: bool = Field(
        description="Whether the success criteria have been met"
    )
    user_input_needed: bool = Field(
        description="True if more input is needed from the user..."
    )

# Used in LLM structured output
evaluator_llm = ChatOpenAI(model="gpt-4o-mini")
evaluator_llm_with_output = evaluator_llm.with_structured_output(EvaluatorOutput)

# Invoke returns EvaluatorOutput
eval_result: EvaluatorOutput = evaluator_llm_with_output.invoke(messages)
```

### 6. Type Hints for Dicts with Known Keys

#### Pattern: State Dictionary
```python
# TypedDict defines structure
class State(TypedDict):
    messages: Annotated[List[Any], add_messages]
    success_criteria: str
    feedback_on_work: Optional[str]
    success_criteria_met: bool
    user_input_needed: bool

# Usage: passing State ensures type safety
def worker(self, state: State) -> Dict[str, Any]:
    # Accessing known keys
    messages: List[Any] = state["messages"]
    success_criteria: str = state["success_criteria"]
```

#### Pattern: Conversation History
```python
# List of dicts with known structure
async def run_superstep(
    self,
    message: str,
    success_criteria: Optional[str],
    history: List[Dict[str, str]]  # list of {"role": ..., "content": ...}
) -> List[Dict[str, str]]:
    user: Dict[str, str] = {"role": "user", "content": message}
    reply: Dict[str, str] = {"role": "assistant", "content": ...}
    return history + [user, reply]
```

## Type Checking Readiness

### Preparation for mypy

The codebase is now ready for static type checking:

```bash
# Basic check
mypy src/

# Strict mode (recommended)
mypy src/ --strict

# With config file
mypy src/ --config-file=mypy.ini
```

#### Recommended mypy Config
```ini
[mypy]
python_version = 3.13
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
no_implicit_optional = True
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True
check_untyped_defs = True
```

### Type Checking Coverage

| Module | Status | Details |
|--------|--------|---------|
| sidekick.py | ✅ Ready | All functions fully typed, all attributes typed |
| app.py | ✅ Ready | All async functions fully typed |
| sidekick_tools.py | ✅ Ready | All tool functions fully typed |
| llm_invocation.py | ⚠️ Partial | Already has error handling type hints |
| main.py | ⚠️ Minimal | Simple entry point, can be enhanced |

## Common Type Patterns in Codebase

### 1. LangGraph State Pattern
```python
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class State(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]  # Reducer pattern
    other_key: str
```

### 2. Async Tool Functions Pattern
```python
from typing import List, Tuple
from langchain_core.tools import BaseTool

async def tool_function() -> List[BaseTool]:
    """Load and return tools."""
    tools: List[BaseTool] = []
    # ... build tools
    return tools
```

### 3. LLM Invocation Pattern
```python
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

class OutputModel(BaseModel):
    field: str

llm = ChatOpenAI(model="gpt-4o-mini")
llm_with_output = llm.with_structured_output(OutputModel)

result: OutputModel = llm_with_output.invoke(messages)
```

### 4. Error Handling Pattern
```python
from typing import Dict, Any

def method(self, state: State) -> Dict[str, Any]:
    try:
        result = invoke_with_retry_sync(
            lambda: self.llm.invoke(messages),
            max_retries=3,
            initial_delay=1.0,
            operation_name="Operation name"
        )
    except LLMInvocationError as e:
        logger.error(f"Operation failed: {e}", exc_info=True)
        return {"error": str(e)}

    return {"result": result}
```

## IDE & Tooling Integration

### PyCharm / IntelliJ IDEA
- ✅ Full type hint support
- ✅ Autocomplete works with type hints
- ✅ Inspection warnings for type mismatches
- ✅ Jump to definition respects types

### VS Code with Pylance
- ✅ Real-time type checking
- ✅ Hover information shows types
- ✅ Quick fixes for type errors
- ✅ Type stub generation

### Command Line Type Checking
```bash
# Install mypy
pip install mypy

# Check all Python files
mypy src/

# Check specific file
mypy src/sidekick.py

# Generate type coverage report
mypy src/ --html report/
```

## Remaining Opportunities

### For Future Enhancement

1. **Protocol Types** (advanced):
   ```python
   from typing import Protocol

   class Runnable(Protocol):
       def invoke(self, input: Any) -> Any: ...
       def batch(self, inputs: List[Any]) -> List[Any]: ...
   ```

2. **Generic Types** (for reusable code):
   ```python
   from typing import TypeVar, Generic

   T = TypeVar('T')

   class Container(Generic[T]):
       def get(self) -> T: ...
   ```

3. **Literal Types** (for constants):
   ```python
   from typing import Literal

   def route(decision: Literal["tools", "evaluator"]) -> None: ...
   ```

4. **TypedDict Inheritance** (for extension):
   ```python
   class BaseState(TypedDict):
       messages: List[BaseMessage]

   class ExtendedState(BaseState):
       metadata: Dict[str, Any]
   ```

## Testing Type Hints

### Test File Structure
```
tests/test_type_hints.py
├── TestTypeAnnotationCompleteness
│   ├── test_sidekick_methods_have_return_types
│   ├── test_app_functions_have_return_types
│   └── test_sidekick_tools_functions_have_return_types
├── TestImportStatements
│   ├── test_sidekick_typing_imports
│   ├── test_app_typing_imports
│   └── test_sidekick_tools_typing_imports
├── TestTypeHintConsistency
│   ├── test_state_typedict_defined
│   ├── test_evaluator_output_defined
│   └── test_class_attributes_typed
├── TestDocstrings
│   ├── test_sidekick_methods_documented
│   ├── test_app_functions_documented
│   └── test_sidekick_tools_functions_documented
└── TestVariableTypeAnnotations
    ├── test_worker_local_variables_typed
    ├── test_evaluator_local_variables_typed
    └── test_run_superstep_local_variables_typed
```

### Running Tests
```bash
# All type hint tests
pytest tests/test_type_hints.py -v

# With coverage
pytest tests/test_type_hints.py --cov=src --cov-report=html

# All tests including existing
pytest tests/ -v
```

## Type Hints Best Practices Applied

✅ **Use specific types** instead of `Any` when possible
✅ **Import from `typing`** for Python < 3.10, `from __future__ import annotations` for 3.7+
✅ **Document return types** in docstrings when non-obvious
✅ **Use `Optional[T]`** for values that can be None
✅ **Use `Union[A, B]`** when value can be multiple specific types
✅ **Avoid bare `dict`, `list`, `tuple`** - use parameterized versions
✅ **Add `-> None`** for functions that don't return anything
✅ **Use `TypedDict`** for dict-like objects with known keys
✅ **Add docstrings** explaining Args, Returns, Raises
✅ **Keep types readable** - don't nest too deeply
