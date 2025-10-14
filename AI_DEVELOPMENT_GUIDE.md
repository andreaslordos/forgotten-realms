# AI Development Guide

This guide is specifically written for AI agents working on the Forgotten Realms MUD codebase. Follow these requirements strictly to ensure code quality and maintainability.

## Core Requirements

### 1. Type Safety with mypy

**All code must pass strict mypy type checking.**

#### Running mypy

```bash
python3 -m mypy --ignore-missing-imports --strict . --exclude 'tests' --exclude 'venv'
```

#### Type Checking Standards

- Use type hints for all function parameters and return values
- Use `Optional[T]` for parameters that can be `None`
- Use `Union[T1, T2]` for parameters that can be multiple types
- Use `List[T]`, `Dict[K, V]`, `Set[T]` for collection types
- Import types from `typing` module: `from typing import Optional, Dict, List, Any`

#### Example

```python
from typing import Optional, Dict, List

def process_player_data(
    player_id: str,
    inventory: List[str],
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """Process player data with strict type hints."""
    if metadata is None:
        metadata = {}
    # Implementation here
    return True
```

### 2. Unit Testing Requirements

**All code must have comprehensive unit tests with minimum 80% coverage.**

#### Coverage Requirements

- **Minimum**: 80% code coverage for ALL files
- **Exceptions**: Only `socket_server.py` and `event_handlers.py` are exempt from coverage requirements
- **Enforcement**: Pre-commit hooks block commits below 80% coverage

#### Running Tests

Full test suite with coverage:
```bash
./scripts/run_backend_tests.sh
```

Specific test file:
```bash
python3 -m unittest backend.managers.tests.test_player -v
```

Check coverage manually:
```bash
python3 -m coverage erase
python3 -m coverage run --source=backend --omit='*/tests/*' -m unittest discover -s backend -p 'test_*.py'
python3 -m coverage report --fail-under=80 --sort=cover
```

View detailed coverage report:
```bash
python3 -m coverage html
open htmlcov/index.html
```

### 3. Test File Organization

#### Directory Structure

Tests are organized in parallel `tests/` subdirectories within each module:

```
backend/
├── commands/
│   ├── auth.py
│   ├── combat.py
│   └── tests/
│       ├── __init__.py
│       ├── test_auth.py
│       └── test_combat.py
├── managers/
│   ├── game_state.py
│   ├── player.py
│   └── tests/
│       ├── __init__.py
│       ├── test_game_state.py
│       └── test_player.py
├── models/
│   ├── Player.py
│   ├── Room.py
│   └── tests/
│       ├── __init__.py
│       ├── test_Player.py
│       └── test_Room.py
└── services/
    ├── notifications.py
    └── tests/
        ├── __init__.py
        └── test_notifications.py
```

#### File Naming Convention

- Source file: `foo.py`
- Test file: `test_foo.py`
- Test files must be in a `tests/` subdirectory at the same level as the source file

### 4. Test Function Naming Convention

Test functions must follow this exact pattern:

```
test_{function_name}_{description_of_test}
```

#### Examples

```python
# Testing a function called validate_password
def test_validate_password_accepts_valid_password(self):
    """Test that validate_password accepts a valid password."""
    pass

def test_validate_password_rejects_short_password(self):
    """Test that validate_password rejects passwords under 8 characters."""
    pass

def test_validate_password_rejects_blank_password(self):
    """Test that validate_password rejects blank passwords."""
    pass

def test_validate_password_handles_special_characters(self):
    """Test that validate_password correctly handles special characters."""
    pass
```

### 5. Test Structure Best Practices

#### Use Arrange-Act-Assert Pattern

```python
async def test_handle_password_validates_old_password_success(self):
    """Test handle_password successfully validates old password."""
    # Arrange
    sid = "test_sid"
    self.online_sessions[sid] = {
        "player": self.player,
        "pwd_change": {
            "stage": "old_password",
            "old_password": None,
            "new_password": None,
        },
    }
    cmd = {"original": "oldpass123"}

    mock_auth = Mock()
    mock_auth.login = Mock()
    self.mock_player_manager.auth_manager = mock_auth

    # Act
    await handle_password(
        cmd,
        self.player,
        self.mock_game_state,
        self.mock_player_manager,
        self.online_sessions,
        self.mock_sio,
        self.mock_utils,
    )

    # Assert
    self.assertEqual(
        self.online_sessions[sid]["pwd_change"]["stage"], "new_password"
    )
    self.assertEqual(
        self.online_sessions[sid]["pwd_change"]["old_password"], "oldpass123"
    )
    mock_auth.login.assert_called_once_with(self.player.name, "oldpass123")
```

#### Test Class Organization

Group related tests into classes:

```python
class HandlePasswordInitializationTest(BaseCommandTest):
    """Test handle_password initialization flow."""

    async def test_handle_password_starts_password_change_flow(self):
        """Test handle_password initializes password change flow."""
        pass

    async def test_handle_password_sets_input_type_to_password(self):
        """Test handle_password sets input type to password."""
        pass


class HandlePasswordValidationTest(BaseCommandTest):
    """Test handle_password validation logic."""

    async def test_handle_password_validates_old_password_success(self):
        """Test handle_password successfully validates old password."""
        pass

    async def test_handle_password_rejects_invalid_old_password(self):
        """Test handle_password rejects invalid old password."""
        pass
```

### 6. Writing Comprehensive Tests

For every function, write tests that cover:

1. **Happy path**: Normal operation with valid inputs
2. **Edge cases**: Boundary conditions, empty inputs, maximum values
3. **Error cases**: Invalid inputs, exceptions, error handling
4. **Integration points**: How the function interacts with other components

#### Example Test Coverage for a Function

```python
# Function to test
def calculate_damage(attacker_level: int, weapon_power: int, defender_armor: int) -> int:
    """Calculate damage dealt in combat."""
    base_damage = attacker_level * weapon_power
    damage_after_armor = max(0, base_damage - defender_armor)
    return damage_after_armor


# Comprehensive tests
class CalculateDamageTest(unittest.TestCase):
    """Test calculate_damage function."""

    def test_calculate_damage_returns_correct_value_normal_case(self):
        """Test calculate_damage with typical values."""
        result = calculate_damage(5, 10, 20)
        self.assertEqual(result, 30)  # (5 * 10) - 20 = 30

    def test_calculate_damage_handles_zero_armor(self):
        """Test calculate_damage when defender has no armor."""
        result = calculate_damage(3, 8, 0)
        self.assertEqual(result, 24)  # (3 * 8) - 0 = 24

    def test_calculate_damage_returns_zero_when_armor_exceeds_damage(self):
        """Test calculate_damage returns 0 when armor is higher than base damage."""
        result = calculate_damage(2, 5, 100)
        self.assertEqual(result, 0)  # max(0, (2 * 5) - 100) = 0

    def test_calculate_damage_handles_level_one_attacker(self):
        """Test calculate_damage with level 1 attacker (edge case)."""
        result = calculate_damage(1, 10, 5)
        self.assertEqual(result, 5)  # (1 * 10) - 5 = 5

    def test_calculate_damage_with_high_level_attacker(self):
        """Test calculate_damage with very high level attacker."""
        result = calculate_damage(100, 50, 1000)
        self.assertEqual(result, 4000)  # (100 * 50) - 1000 = 4000
```

### 7. Mocking Best Practices

Use mocks to isolate the code under test:

```python
from unittest.mock import Mock, AsyncMock, patch

# Mock objects
mock_player = Mock()
mock_player.name = "TestPlayer"
mock_player.level = 5

# Mock async functions
mock_async_func = AsyncMock(return_value="success")

# Patch external dependencies
with patch('commands.auth.hash_password', return_value='hashed') as mock_hash:
    result = change_password("test", "newpass")
    mock_hash.assert_called_once_with("newpass")
```

### 8. Pre-commit Hook Enforcement

**All commits are automatically validated:**

```bash
# Install pre-commit hooks
pip install pre-commit coverage mypy
pre-commit install
```

On each commit, the following checks run:
1. **Black**: Automatically formats code
2. **Ruff**: Lints code for common issues
3. **Tests**: All tests must pass
4. **Coverage**: Must maintain 80% minimum coverage

**If any check fails, the commit is blocked.**

### 9. Development Workflow

#### Step 1: Write or Modify Code

Add type hints to all functions:
```python
def process_command(cmd: str, player_id: str) -> Optional[str]:
    """Process a player command."""
    # Implementation
    return result
```

#### Step 2: Write Tests

Create comprehensive tests achieving >80% coverage:
```python
# In tests/test_commands.py
def test_process_command_handles_valid_input(self):
    """Test process_command with valid input."""
    result = process_command("look", "player_123")
    self.assertIsNotNone(result)

def test_process_command_handles_invalid_command(self):
    """Test process_command with invalid command."""
    result = process_command("invalid", "player_123")
    self.assertIsNone(result)
```

#### Step 3: Run Type Checking

```bash
python3 -m mypy --ignore-missing-imports --strict . --exclude 'tests' --exclude 'venv'
```

Fix any type errors before proceeding.

#### Step 4: Run Tests and Check Coverage

```bash
./scripts/run_backend_tests.sh
```

Ensure all tests pass and coverage is ≥80%.

#### Step 5: Commit

```bash
git add .
git commit -m "Add process_command function with comprehensive tests"
```

Pre-commit hooks will automatically validate everything.

### 10. Common Patterns and Examples

#### Testing Async Functions

```python
import unittest

class AsyncTest(unittest.TestCase):
    """Test async functions."""

    async def test_async_function(self):
        """Test an async function."""
        result = await some_async_function()
        self.assertEqual(result, expected_value)
```

#### Testing Exception Handling

```python
def test_function_raises_exception_on_invalid_input(self):
    """Test function raises ValueError for invalid input."""
    with self.assertRaises(ValueError):
        function_under_test(invalid_input)
```

#### Testing with Multiple Assertions

```python
def test_function_returns_correct_data_structure(self):
    """Test function returns properly structured data."""
    result = function_under_test()

    # Multiple assertions to verify structure
    self.assertIsInstance(result, dict)
    self.assertIn("status", result)
    self.assertIn("data", result)
    self.assertEqual(result["status"], "success")
    self.assertIsInstance(result["data"], list)
```

## Summary Checklist

Before submitting any code, verify:

- [ ] All functions have complete type hints
- [ ] mypy passes with `--strict` flag
- [ ] Every function has multiple test cases
- [ ] Test names follow `test_{function_name}_{description}` convention
- [ ] Tests are in the correct `tests/` subdirectory
- [ ] Test file named `test_{source_file}.py`
- [ ] Coverage is ≥80% for all files (except `socket_server.py` and `event_handlers.py`)
- [ ] All tests pass
- [ ] Tests use Arrange-Act-Assert pattern
- [ ] Tests have descriptive docstrings
- [ ] Pre-commit hooks are installed and passing

## Quick Reference Commands

```bash
# Type checking
python3 -m mypy --ignore-missing-imports --strict . --exclude 'tests' --exclude 'venv'

# Run all tests with coverage
./scripts/run_backend_tests.sh

# Run specific test file
python3 -m unittest backend.commands.tests.test_auth -v

# Check coverage for specific module
python3 -m coverage run --source=backend.commands -m unittest discover -s backend/commands/tests
python3 -m coverage report

# Install pre-commit hooks
pip install pre-commit coverage mypy
pre-commit install
```

## Questions?

- See test examples in `backend/commands/tests/test_auth.py`
- Review test script at `scripts/run_backend_tests.sh`
- Check existing modules for type hint patterns
- Refer to Python typing documentation: https://docs.python.org/3/library/typing.html
