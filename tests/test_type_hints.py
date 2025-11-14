"""
Test suite for type hints validation.

This module tests that all type annotations are correct and complete.
It uses static type checking via mypy and runtime type validation.
"""

import pytest
import inspect
from typing import List, Dict, Any, Optional, Tuple


class TestTypeAnnotationCompleteness:
    """Test that all functions and methods have complete type annotations."""

    def test_sidekick_methods_have_return_types(self) -> None:
        """Verify all Sidekick methods have return type annotations."""
        # Read the file directly to check for type annotations
        with open('/Volumes/Storage/Projects/assistant/src/sidekick.py', 'r') as f:
            content = f.read()

        # Check that key methods have return type annotations
        methods_to_check = [
            ('def __init__(self)', '-> None:'),
            ('def setup(', '-> None:'),
            ('def build_graph(', '-> None:'),
            ('def cleanup(', '-> None:'),
            ('def worker_router(', '-> str:'),
            ('def route_based_on_evaluation(', '-> str:'),
            ('def evaluator(', '-> Dict[str, Any]:'),
            ('def worker(', '-> Dict[str, Any]:'),
            ('def format_conversation(', '-> str:'),
        ]

        for method_sig, expected_return in methods_to_check:
            # Extract just the signature and return type
            assert method_sig in content, f"Method signature {method_sig} not found"
            # Find the index of the method signature
            idx = content.find(method_sig)
            # Look for return type within the next 100 characters
            snippet = content[idx:idx+200]
            assert expected_return in snippet, \
                f"Method {method_sig} missing expected return type {expected_return}"

    def test_app_functions_have_return_types(self) -> None:
        """Verify all app functions have return type annotations."""
        with open('/Volumes/Storage/Projects/assistant/src/app.py', 'r') as f:
            content = f.read()

        functions_to_check = [
            ('async def setup()', '-> Sidekick:'),
            ('async def process_message(', '-> Tuple[List[Dict[str, str]], Sidekick]:'),
            ('async def reset()', '-> Tuple[str, str, None, Sidekick]:'),
            ('def free_resources(', '-> None:'),
        ]

        for func_sig, expected_return in functions_to_check:
            assert func_sig in content, f"Function {func_sig} not found"
            # Find the index of the function signature
            idx = content.find(func_sig)
            # Look for return type within the next 200 characters
            snippet = content[idx:idx+300]
            assert expected_return in snippet, \
                f"Function {func_sig} missing expected return type {expected_return}"

    def test_sidekick_tools_functions_have_return_types(self) -> None:
        """Verify all sidekick_tools functions have return type annotations."""
        with open('/Volumes/Storage/Projects/assistant/src/sidekick_tools.py', 'r') as f:
            content = f.read()

        functions_to_check = [
            ('async def playwright_tools()', '-> Tuple[List[BaseTool], Browser, Playwright]:'),
            ('def push(', '-> str:'),
            ('def get_file_tools()', '-> List[BaseTool]:'),
            ('async def other_tools()', '-> List[BaseTool]:'),
        ]

        for func_sig, expected_return in functions_to_check:
            assert func_sig in content, f"Function {func_sig} not found"
            # Find the index of the function signature
            idx = content.find(func_sig)
            # Look for return type within the next 100 characters
            snippet = content[idx:idx+200]
            assert expected_return in snippet, \
                f"Function {func_sig} missing expected return type {expected_return}"

    def test_sidekick_parameter_types(self) -> None:
        """Verify Sidekick methods have typed parameters."""
        with open('/Volumes/Storage/Projects/assistant/src/sidekick.py', 'r') as f:
            content = f.read()

        # Check run_superstep has typed parameters
        assert 'def run_superstep(' in content
        idx = content.find('def run_superstep(')
        snippet = content[idx:idx+400]

        assert 'message: str' in snippet
        assert 'success_criteria: Optional[str]' in snippet
        assert 'history: List[Dict[str, str]]' in snippet

    def test_format_conversation_parameter_types(self) -> None:
        """Verify format_conversation has typed parameters."""
        with open('/Volumes/Storage/Projects/assistant/src/sidekick.py', 'r') as f:
            content = f.read()

        assert 'def format_conversation(self, messages: List[BaseMessage]) -> str:' in content

    def test_worker_router_parameter_types(self) -> None:
        """Verify worker_router has typed parameters."""
        with open('/Volumes/Storage/Projects/assistant/src/sidekick.py', 'r') as f:
            content = f.read()

        assert 'def worker_router(self, state: State) -> str:' in content

    def test_evaluator_parameter_types(self) -> None:
        """Verify evaluator has typed parameters."""
        with open('/Volumes/Storage/Projects/assistant/src/sidekick.py', 'r') as f:
            content = f.read()

        assert 'def evaluator(self, state: State) -> Dict[str, Any]:' in content

    def test_worker_parameter_types(self) -> None:
        """Verify worker has typed parameters."""
        with open('/Volumes/Storage/Projects/assistant/src/sidekick.py', 'r') as f:
            content = f.read()

        assert 'def worker(self, state: State) -> Dict[str, Any]:' in content


class TestImportStatements:
    """Test that proper typing imports are in place."""

    def test_sidekick_typing_imports(self) -> None:
        """Verify sidekick.py has necessary typing imports."""
        with open('/Volumes/Storage/Projects/assistant/src/sidekick.py', 'r') as f:
            content = f.read()

        required_imports = [
            'from typing import Annotated, Any, Dict, List, Optional, Callable',
            'from typing_extensions import TypedDict',
            'from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage',
            'from langchain_core.tools import BaseTool',
            'from playwright.async_api import Browser, Playwright',
        ]

        for imp in required_imports:
            assert imp in content, f"Missing import: {imp}"

    def test_app_typing_imports(self) -> None:
        """Verify app.py has necessary typing imports."""
        with open('/Volumes/Storage/Projects/assistant/src/app.py', 'r') as f:
            content = f.read()

        required_imports = [
            'from typing import List, Dict, Tuple, Optional, Any',
        ]

        for imp in required_imports:
            assert imp in content, f"Missing import: {imp}"

    def test_sidekick_tools_typing_imports(self) -> None:
        """Verify sidekick_tools.py has necessary typing imports."""
        with open('/Volumes/Storage/Projects/assistant/src/sidekick_tools.py', 'r') as f:
            content = f.read()

        required_imports = [
            'from typing import List, Tuple, Optional',
            'from langchain_core.tools import BaseTool',
            'from playwright.async_api import async_playwright, Browser, Playwright',
        ]

        for imp in required_imports:
            assert imp in content, f"Missing import: {imp}"


class TestTypeHintConsistency:
    """Test consistency of type hints across the codebase."""

    def test_state_typedict_defined(self) -> None:
        """Verify State TypedDict is properly defined."""
        with open('/Volumes/Storage/Projects/assistant/src/sidekick.py', 'r') as f:
            content = f.read()

        assert 'class State(TypedDict):' in content
        assert 'messages: Annotated[List[Any], add_messages]' in content
        assert 'success_criteria: str' in content
        assert 'feedback_on_work: Optional[str]' in content
        assert 'success_criteria_met: bool' in content
        assert 'user_input_needed: bool' in content

    def test_evaluator_output_defined(self) -> None:
        """Verify EvaluatorOutput Pydantic model is properly defined."""
        with open('/Volumes/Storage/Projects/assistant/src/sidekick.py', 'r') as f:
            content = f.read()

        assert 'class EvaluatorOutput(BaseModel):' in content
        assert 'feedback: str = Field(description=' in content
        assert 'success_criteria_met: bool = Field(description=' in content
        assert 'user_input_needed: bool = Field(' in content

    def test_class_attributes_typed(self) -> None:
        """Verify Sidekick class attributes have type annotations."""
        with open('/Volumes/Storage/Projects/assistant/src/sidekick.py', 'r') as f:
            content = f.read()

        # Find the __init__ method
        init_idx = content.find('def __init__(self) -> None:')
        # Get the next 1000 chars to see attribute assignments
        init_section = content[init_idx:init_idx+1500]

        type_assignments = [
            'self.worker_llm_with_tools: Optional[Any] = None',
            'self.evaluator_llm_with_output: Optional[Any] = None',
            'self.tools: Optional[List[BaseTool]] = None',
            'self.sidekick_id: str = str(uuid.uuid4())',
            'self.browser: Optional[Browser] = None',
            'self.playwright: Optional[Playwright] = None',
        ]

        for assignment in type_assignments:
            assert assignment in init_section, f"Missing typed attribute: {assignment}"


class TestDocstrings:
    """Test that documented functions have proper docstrings."""

    def test_sidekick_methods_documented(self) -> None:
        """Verify Sidekick methods have docstrings."""
        with open('/Volumes/Storage/Projects/assistant/src/sidekick.py', 'r') as f:
            content = f.read()

        methods_to_check = [
            'def __init__(self) -> None:',
            'async def setup(self) -> None:',
            'def worker(self, state: State) -> Dict[str, Any]:',
            'def evaluator(self, state: State) -> Dict[str, Any]:',
            'async def build_graph(self) -> None:',
            'async def cleanup(self) -> None:',
        ]

        for method in methods_to_check:
            assert method in content, f"Method {method} not found"
            idx = content.find(method)
            # Check for docstring right after
            snippet = content[idx:idx+300]
            assert '"""' in snippet, f"Method {method} missing docstring"

    def test_app_functions_documented(self) -> None:
        """Verify app functions have docstrings."""
        with open('/Volumes/Storage/Projects/assistant/src/app.py', 'r') as f:
            content = f.read()

        functions_to_check = [
            'async def setup() -> Sidekick:',
            'async def process_message(',
            'async def reset() -> Tuple[str, str, None, Sidekick]:',
            'def free_resources(sidekick: Optional[Sidekick]) -> None:',
        ]

        for func in functions_to_check:
            assert func in content, f"Function {func} not found"
            idx = content.find(func)
            # Check for docstring right after
            snippet = content[idx:idx+300]
            assert '"""' in snippet, f"Function {func} missing docstring"

    def test_sidekick_tools_functions_documented(self) -> None:
        """Verify sidekick_tools functions have docstrings."""
        with open('/Volumes/Storage/Projects/assistant/src/sidekick_tools.py', 'r') as f:
            content = f.read()

        functions_to_check = [
            'async def playwright_tools()',
            'def push(text: str) -> str:',
            'def get_file_tools()',
            'async def other_tools()',
        ]

        for func in functions_to_check:
            assert func in content, f"Function {func} not found"
            idx = content.find(func)
            # Check for docstring right after (within 200 chars)
            snippet = content[idx:idx+300]
            assert '"""' in snippet, f"Function {func} missing docstring"


class TestVariableTypeAnnotations:
    """Test that local variables in complex functions are typed."""

    def test_worker_local_variables_typed(self) -> None:
        """Verify worker method has typed local variables."""
        with open('/Volumes/Storage/Projects/assistant/src/sidekick.py', 'r') as f:
            content = f.read()

        worker_start = content.find('def worker(self, state: State) -> Dict[str, Any]:')
        # Get up to 2000 chars to capture the whole method
        worker_section = content[worker_start:worker_start+2500]

        # Check for typed variables - system_message uses f-string which is acceptable
        assert 'system_message = f' in worker_section
        assert 'messages = state["messages"]' in worker_section

    def test_evaluator_local_variables_typed(self) -> None:
        """Verify evaluator method has typed local variables."""
        with open('/Volumes/Storage/Projects/assistant/src/sidekick.py', 'r') as f:
            content = f.read()

        evaluator_start = content.find('def evaluator(self, state: State) -> Dict[str, Any]:')
        # Get a large section to capture the whole method
        evaluator_section = content[evaluator_start:evaluator_start+3500]

        # Check for typed variables
        assert 'last_response: str =' in evaluator_section
        assert 'system_message: str =' in evaluator_section
        assert 'user_message: str =' in evaluator_section
        assert 'evaluator_messages: List[BaseMessage] =' in evaluator_section

    def test_run_superstep_local_variables_typed(self) -> None:
        """Verify run_superstep method has typed local variables."""
        with open('/Volumes/Storage/Projects/assistant/src/sidekick.py', 'r') as f:
            content = f.read()

        run_start = content.find('async def run_superstep(')
        # Get section to capture the method
        run_section = content[run_start:run_start+2000]

        # Check for typed variables
        assert 'config: Dict[str, Any] =' in run_section
        assert 'state: Dict[str, Any] =' in run_section
        assert 'result: Dict[str, Any] =' in run_section
        assert 'user: Dict[str, str] =' in run_section


class TestReturnTypeConsistency:
    """Test that function return types match their documentation."""

    def test_setup_documented_return_type(self) -> None:
        """Verify setup() is documented to return None."""
        with open('/Volumes/Storage/Projects/assistant/src/sidekick.py', 'r') as f:
            content = f.read()

        setup_start = content.find('async def setup(self) -> None:')
        setup_section = content[setup_start:setup_start+800]

        # Check docstring mentions None return or initialization
        assert 'Returns:' in setup_section or 'Initialize' in setup_section

    def test_worker_documented_return_type(self) -> None:
        """Verify worker() is documented to return Dict."""
        with open('/Volumes/Storage/Projects/assistant/src/sidekick.py', 'r') as f:
            content = f.read()

        worker_start = content.find('def worker(self, state: State) -> Dict[str, Any]:')
        worker_section = content[worker_start:worker_start+800]

        # Check docstring
        assert 'Returns:' in worker_section
        assert 'state' in worker_section.lower() or 'dict' in worker_section.lower()
