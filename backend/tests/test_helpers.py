"""
Reusable test fixtures and helper functions for test suite.

This module provides:
- Mock object factories
- Common test data generators
- Reusable patch decorators
"""

from unittest.mock import Mock, AsyncMock, patch
from functools import wraps


def create_mock_player(name="TestPlayer", level="Novice", **kwargs):
    """
    Create a mock player with default attributes.

    Args:
        name: Player name
        level: Player level
        **kwargs: Additional attributes to override defaults

    Returns:
        Mock player object
    """
    player = Mock()
    player.name = name
    player.level = level
    player.health = kwargs.get('health', 100)
    player.max_health = kwargs.get('max_health', 100)
    player.strength = kwargs.get('strength', 10)
    player.dexterity = kwargs.get('dexterity', 10)
    player.constitution = kwargs.get('constitution', 10)
    player.intelligence = kwargs.get('intelligence', 10)
    player.wisdom = kwargs.get('wisdom', 10)
    player.charisma = kwargs.get('charisma', 10)
    player.inventory = kwargs.get('inventory', [])
    player.location = kwargs.get('location', "test_room_1")
    player.points = kwargs.get('points', 0)
    player.gold = kwargs.get('gold', 0)
    player.combat_target = kwargs.get('combat_target', None)
    player.is_sleeping = kwargs.get('is_sleeping', False)
    player.level_up = Mock()
    player.to_dict = Mock(return_value={'name': name, 'level': level})
    player.save = Mock()
    return player


def create_mock_mobile(name="TestMob", **kwargs):
    """
    Create a mock mobile/NPC.

    Args:
        name: Mobile name
        **kwargs: Additional attributes to override defaults

    Returns:
        Mock mobile object
    """
    mob = Mock()
    mob.name = name
    mob.health = kwargs.get('health', 50)
    mob.max_health = kwargs.get('max_health', 50)
    mob.level = kwargs.get('level', 1)
    mob.strength = kwargs.get('strength', 8)
    mob.location = kwargs.get('location', "test_room_1")
    mob.is_dead = kwargs.get('is_dead', False)
    mob.combat_target = kwargs.get('combat_target', None)
    mob.loot = kwargs.get('loot', [])
    mob.respawn_time = kwargs.get('respawn_time', 300)
    mob.aggressive = kwargs.get('aggressive', False)
    mob.to_dict = Mock(return_value={'name': name, 'health': mob.health})
    return mob


def create_mock_item(name="TestItem", **kwargs):
    """
    Create a mock item.

    Args:
        name: Item name
        **kwargs: Additional attributes to override defaults

    Returns:
        Mock item object
    """
    item = Mock()
    item.name = name
    item.description = kwargs.get('description', f"A {name}")
    item.weight = kwargs.get('weight', 1)
    item.value = kwargs.get('value', 10)
    item.item_type = kwargs.get('item_type', 'misc')
    item.is_container = kwargs.get('is_container', False)
    item.contents = kwargs.get('contents', [])
    item.is_weapon = kwargs.get('is_weapon', False)
    item.damage = kwargs.get('damage', 0)
    item.to_dict = Mock(return_value={'name': name, 'type': item.item_type})
    return item


def create_mock_room(room_id="test_room_1", **kwargs):
    """
    Create a mock room.

    Args:
        room_id: Room identifier
        **kwargs: Additional attributes to override defaults

    Returns:
        Mock room object
    """
    room = Mock()
    room.id = room_id
    room.name = kwargs.get('name', "Test Room")
    room.description = kwargs.get('description', "A test room.")
    room.exits = kwargs.get('exits', {})
    room.items = kwargs.get('items', [])
    room.mobs = kwargs.get('mobs', [])
    room.players = kwargs.get('players', [])
    room.features = kwargs.get('features', [])
    room.to_dict = Mock(return_value={'id': room_id, 'name': room.name})
    return room


def create_mock_sio():
    """
    Create a mock SocketIO instance.

    Returns:
        AsyncMock SocketIO object
    """
    sio = AsyncMock()
    sio.emit = AsyncMock()
    sio.disconnect = AsyncMock()
    sio.enter_room = AsyncMock()
    sio.leave_room = AsyncMock()
    return sio


def create_mock_utils():
    """
    Create a mock utils module.

    Returns:
        Mock utils object with async methods
    """
    utils = Mock()
    utils.send_message = AsyncMock()
    utils.send_stats_update = AsyncMock()
    utils.broadcast_to_room = AsyncMock()
    utils.send_room_update = AsyncMock()
    utils.send_inventory_update = AsyncMock()
    utils.format_health_bar = Mock(return_value="[##########] 100%")
    return utils


def create_mock_game_state(**kwargs):
    """
    Create a mock game state.

    Args:
        **kwargs: Additional attributes to override defaults

    Returns:
        Mock game state object
    """
    game_state = Mock()
    game_state.rooms = kwargs.get('rooms', {})
    game_state.items = kwargs.get('items', {})
    game_state.mobs = kwargs.get('mobs', {})
    game_state.players = kwargs.get('players', {})
    game_state.get_room = Mock(side_effect=lambda rid: game_state.rooms.get(rid))
    return game_state


def create_mock_player_manager():
    """
    Create a mock player manager.

    Returns:
        Mock player manager object
    """
    manager = Mock()
    manager.login = Mock()
    manager.logout = Mock()
    manager.save_players = Mock()
    manager.load_player = Mock()
    manager.create_player = Mock()
    manager.player_exists = Mock(return_value=False)
    return manager


def create_online_sessions(*players):
    """
    Create a mock online sessions dictionary.

    Args:
        *players: Player objects to add as online (creates mock SIDs)

    Returns:
        Dictionary mapping SIDs to session data
    """
    sessions = {}
    for i, player in enumerate(players):
        sid = f"test_sid_{i}"
        sessions[sid] = {
            'player': player,
            'connected_at': '2025-01-01T00:00:00'
        }
    return sessions


def patch_file_operations(test_func):
    """
    Decorator to patch common file operations.

    Patches:
    - builtins.open
    - json.load
    - json.dump
    """
    @wraps(test_func)
    @patch('builtins.open', create=True)
    @patch('json.load')
    @patch('json.dump')
    def wrapper(*args, **kwargs):
        return test_func(*args, **kwargs)
    return wrapper


def patch_socket_operations(test_func):
    """
    Decorator to patch socket operations.

    Note: Specific module paths should be adjusted per test file.
    """
    @wraps(test_func)
    def wrapper(*args, **kwargs):
        return test_func(*args, **kwargs)
    return wrapper


def patch_async_sleep(test_func):
    """
    Decorator to patch asyncio.sleep for faster tests.
    """
    @wraps(test_func)
    @patch('asyncio.sleep', new_callable=AsyncMock)
    def wrapper(*args, **kwargs):
        return test_func(*args, **kwargs)
    return wrapper
