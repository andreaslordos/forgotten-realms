# Test Writing Instructions

## Overview

This document outlines the testing requirements and conventions for the Forgotten Realms MUD backend. Following these conventions is **CRITICAL** for maintaining a clean, organized, and maintainable test suite.

## Directory Structure & Naming Conventions

### ⚠️ CRITICAL: Test Organization Rules

1. **Each module MUST have its own `tests/` subdirectory**
   ```
   commands/
   ├── tests/
   │   ├── __init__.py
   │   └── test_*.py
   models/
   ├── tests/
   │   ├── __init__.py
   │   └── test_*.py
   managers/
   ├── tests/
   │   ├── __init__.py
   │   └── test_*.py
   services/
   ├── tests/
   │   ├── __init__.py
   │   └── test_*.py
   ```

2. **Test File Naming Convention**
   - Format: `test_{module_name}.py`
   - Example: For `combat.py` → create `test_combat.py`
   - Example: For `mob_manager.py` → create `test_mob_manager.py`

3. **Test Function Naming Convention**
   - Format: `test_{function_name}_{specific_descriptor}`
   - The function name MUST be included in the test name
   - Be specific about what scenario is being tested

   **Good Examples:**
   ```python
   def test___init___with_all_parameters(self):
   def test_add_item_adds_to_list(self):
   def test_remove_item_returns_none_when_not_found(self):
   def test_can_use_returns_false_insufficient_strength(self):
   def test_to_dict_includes_all_attributes(self):
   ```

   **Bad Examples:**
   ```python
   def test_initialization(self):  # ❌ Which function?
   def test_item_works(self):      # ❌ Too vague
   def test_success_case(self):     # ❌ No function name
   ```

4. **Import Path Convention**
   - All test files should use: `sys.path.insert(0, str(Path(__file__).resolve().parents[2]))`
   - This ensures imports work regardless of how tests are run

## Testing Best Practices

### Use Mocking & Patching Liberally

**DO use mocks for:**
- Database/file I/O operations
- Network calls
- Socket operations
- External dependencies
- Async operations (use `AsyncMock`)
- Time-dependent operations

**Example:**
```python
from unittest.mock import Mock, AsyncMock, patch

class TestCombat(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_sio = AsyncMock()
        self.mock_utils = Mock()
        self.mock_utils.send_message = AsyncMock()

    @patch('commands.combat.process_combat_tick', new_callable=AsyncMock)
    async def test_attack_triggers_combat_tick(self, mock_combat_tick):
        # Test implementation
        pass
```

### Reusing Mocks, Fixtures, and Patches

**Creating Reusable Test Fixtures:**

To avoid duplicating mock setup across multiple test files, create shared fixtures and helper functions:

**1. Create a test helpers/fixtures module:**
```python
# tests/test_helpers.py or tests/fixtures.py
from unittest.mock import Mock, AsyncMock

def create_mock_player(name="TestPlayer", level="Novice", **kwargs):
    """Create a mock player with default attributes."""
    player = Mock()
    player.name = name
    player.level = level
    player.health = kwargs.get('health', 100)
    player.max_health = kwargs.get('max_health', 100)
    player.strength = kwargs.get('strength', 10)
    player.inventory = kwargs.get('inventory', [])
    player.location = kwargs.get('location', "test_room_1")
    player.points = kwargs.get('points', 0)
    player.level_up = Mock()
    player.to_dict = Mock(return_value={'name': name, 'level': level})
    return player

def create_mock_sio():
    """Create a mock SocketIO instance."""
    sio = AsyncMock()
    sio.emit = AsyncMock()
    sio.disconnect = AsyncMock()
    return sio

def create_mock_utils():
    """Create a mock utils module."""
    utils = Mock()
    utils.send_message = AsyncMock()
    utils.send_stats_update = AsyncMock()
    utils.broadcast_to_room = AsyncMock()
    return utils

def create_mock_game_state():
    """Create a mock game state."""
    game_state = Mock()
    game_state.rooms = {}
    game_state.items = {}
    game_state.mobs = {}
    return game_state
```

**2. Import and use in your tests:**
```python
# In your test file
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.test_helpers import (
    create_mock_player,
    create_mock_sio,
    create_mock_utils,
    create_mock_game_state
)

class MyTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Use shared fixtures
        self.player = create_mock_player(name="Hero", level="Champion")
        self.sio = create_mock_sio()
        self.utils = create_mock_utils()
        self.game_state = create_mock_game_state()
```

**3. Create reusable patch decorators:**
```python
# tests/test_helpers.py
from functools import wraps
from unittest.mock import patch, AsyncMock

def patch_file_operations(test_func):
    """Decorator to patch common file operations."""
    @wraps(test_func)
    @patch('builtins.open', create=True)
    @patch('json.load')
    @patch('json.dump')
    def wrapper(*args, **kwargs):
        return test_func(*args, **kwargs)
    return wrapper

def patch_socket_operations(test_func):
    """Decorator to patch socket operations."""
    @wraps(test_func)
    @patch('utils.send_message', new_callable=AsyncMock)
    @patch('utils.broadcast_to_room', new_callable=AsyncMock)
    def wrapper(*args, **kwargs):
        return test_func(*args, **kwargs)
    return wrapper
```

**4. Create base test classes for common setups:**
```python
# tests/test_base.py
import unittest
from unittest.mock import Mock, AsyncMock

class BaseCommandTest(unittest.IsolatedAsyncioTestCase):
    """Base class for command tests with common setup."""

    def setUp(self):
        """Set up common command test fixtures."""
        self.mock_sio = AsyncMock()
        self.mock_utils = Mock()
        self.mock_utils.send_message = AsyncMock()
        self.mock_utils.broadcast_to_room = AsyncMock()
        self.mock_game_state = Mock()
        self.mock_player_manager = Mock()
        self.online_sessions = {}

class BaseModelTest(unittest.TestCase):
    """Base class for model tests with common setup."""

    def setUp(self):
        """Set up common model test fixtures."""
        self.test_data = {}

class BaseAsyncTest(unittest.IsolatedAsyncioTestCase):
    """Base class for async tests with common async fixtures."""

    def setUp(self):
        """Set up common async test fixtures."""
        self.mock_sio = AsyncMock()
```

**5. Usage example with inheritance:**
```python
from tests.test_base import BaseCommandTest

class TestMyCommand(BaseCommandTest):
    """Tests inherit all fixtures from BaseCommandTest."""

    def setUp(self):
        super().setUp()  # Get all base fixtures
        # Add command-specific fixtures
        self.specific_mock = Mock()
```

**Benefits:**
- **DRY Principle**: Don't repeat mock setup across files
- **Consistency**: All tests use same mock structure
- **Maintainability**: Update mock in one place
- **Readability**: Tests focus on what's being tested, not setup
- **Speed**: Faster test development

### Write Thorough Tests

**Each module should test:**
1. **Happy path scenarios** - Normal, expected behavior
2. **Edge cases** - Boundary conditions, empty inputs, maximum values
3. **Error conditions** - Invalid inputs, missing data, exceptions
4. **State changes** - Verify object/system state after operations
5. **Integration points** - How the module interacts with others

**Test Coverage Goals:**
- Aim for **80%+ line coverage** per module
- Near **100% coverage** for critical business logic (combat, player stats, inventory)
- Test both success and failure paths for every function

### Test Class Organization

```python
class FunctionNameTest(unittest.TestCase):
    """Test {function_name} functionality."""

    def setUp(self):
        """Set up common test fixtures."""
        # Initialize test data

    def test_{function_name}_{scenario_1}(self):
        """Test {function_name} when {scenario_1}."""
        # Arrange
        # Act
        # Assert

    def test_{function_name}_{scenario_2}(self):
        """Test {function_name} when {scenario_2}."""
        pass
```

**Group related tests into test classes:**
- Initialization tests → `{ClassName}InitializationTest`
- Serialization tests → `{ClassName}SerializationTest`
- Validation tests → `{ClassName}ValidationTest`

### Run All Tests
```bash
# From backend directory
python3 -m unittest discover -s . -p "test_*.py"
```

### Run Tests by Module
```bash
# Commands tests
python3 -m unittest discover -s commands/tests -v

# Models tests
python3 -m unittest discover -s models/tests -v

# Managers tests
python3 -m unittest discover -s managers/tests -v

# Services tests
python3 -m unittest discover -s services/tests -v
```

### Run Single Test File
```bash
python3 commands/tests/test_combat.py
```

### Check Coverage
```bash
python -m unittest discover; python3 -m coverage report --omit="*/tests/*" --sort=cover
```

## Test Template

Use this template when creating new test files:

```python
"""
Comprehensive tests for {module_name} module.

Tests cover:
- {functionality_1}
- {functionality_2}
- {functionality_3}
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from {module} import {functions/classes}


class AsyncTestCase(unittest.IsolatedAsyncioTestCase):
    """Base class for async tests."""

    def setUp(self):
        """Set up common test fixtures."""
        # Initialize mocks
        self.mock_sio = AsyncMock()
        self.mock_utils = Mock()
        self.mock_utils.send_message = AsyncMock()

        # Initialize test data
        pass


class FunctionNameTest(AsyncTestCase):  # or unittest.TestCase for sync tests
    """Test {function_name} functionality."""

    def test_{function_name}_{scenario}(self):
        """Test {function_name} when {scenario}."""
        # Arrange - Set up test data

        # Act - Call the function

        # Assert - Verify results
        pass


if __name__ == "__main__":
    unittest.main()
```

## Why These Conventions Matter

1. **Maintainability** - Consistent structure makes tests easy to find and modify
2. **Clarity** - Explicit function names make test purpose immediately clear
3. **Coverage** - Organized tests ensure comprehensive coverage
4. **Debugging** - When a test fails, the name tells you exactly what broke
5. **Collaboration** - Team members can navigate tests without confusion
6. **CI/CD** - Automated systems can discover and run all tests reliably

## Questions?

If you're unsure how to test something:
1. Look at existing tests in the same module for examples
2. Check if similar functionality is tested elsewhere
3. Ask for guidance on complex async operations or mocking scenarios

**Remember: Good tests are an investment in code quality and team productivity!**
