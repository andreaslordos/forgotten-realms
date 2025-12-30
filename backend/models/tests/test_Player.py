"""
Comprehensive tests for Player model - CRITICAL.

Tests cover:
- Player initialization
- Leveling system
- Inventory management
- Point system
- Stat calculations
- Serialization
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.test_base import BaseModelTest
from tests.test_helpers import create_mock_item
from models.Player import Player
from models.Levels import levels
from backend.globals import SPAWN_ROOM


class PlayerInitializationTest(BaseModelTest):
    """Test Player initialization."""

    def test___init___creates_player_with_name(self):
        """Test __init__ creates player with given name."""
        player = Player("TestPlayer")
        self.assertEqual(player.name, "TestPlayer")

    def test___init___sets_default_sex_to_male(self):
        """Test __init__ sets default sex to M."""
        player = Player("TestPlayer")
        self.assertEqual(player.sex, "M")

    def test___init___accepts_custom_sex(self):
        """Test __init__ accepts custom sex parameter."""
        player = Player("TestPlayer", sex="F")
        self.assertEqual(player.sex, "F")

    def test___init___sets_email(self):
        """Test __init__ sets email when provided."""
        player = Player("TestPlayer", email="test@example.com")
        self.assertEqual(player.email, "test@example.com")

    def test___init___sets_default_spawn_room(self):
        """Test __init__ sets default spawn room to the right spawn room."""
        player = Player("TestPlayer")
        self.assertEqual(player.current_room, SPAWN_ROOM)

    def test___init___accepts_custom_spawn_room(self):
        """Test __init__ accepts custom spawn room."""
        player = Player("TestPlayer", spawn_room="custom_room")
        self.assertEqual(player.current_room, "custom_room")

    def test___init___sets_points_to_zero(self):
        """Test __init__ sets points to zero."""
        player = Player("TestPlayer")
        self.assertEqual(player.points, 0)

    def test___init___initializes_empty_inventory(self):
        """Test __init__ initializes empty inventory list."""
        player = Player("TestPlayer")
        self.assertIsInstance(player.inventory, list)
        self.assertEqual(len(player.inventory), 0)

    def test___init___sets_starting_level_stats(self):
        """Test __init__ sets stats from level 0."""
        player = Player("TestPlayer")
        self.assertEqual(player.level, levels[0]["name"])
        self.assertEqual(player.stamina, levels[0]["stamina"])
        self.assertEqual(player.max_stamina, levels[0]["stamina"])
        self.assertEqual(player.strength, levels[0]["strength"])
        self.assertEqual(player.dexterity, levels[0]["dexterity"])
        self.assertEqual(player.magic, levels[0]["magic"])

    def test___init___sets_created_at_timestamp(self):
        """Test __init__ sets created_at timestamp."""
        player = Player("TestPlayer")
        self.assertIsInstance(player.created_at, datetime)

    def test___init___sets_last_active_timestamp(self):
        """Test __init__ sets last_active timestamp."""
        player = Player("TestPlayer")
        self.assertIsInstance(player.last_active, datetime)


class PlayerLevelUpTest(unittest.TestCase):
    """Test Player.level_up functionality."""

    def test_level_up_increases_level_when_points_sufficient(self):
        """Test level_up increases level when points are sufficient."""
        player = Player("TestPlayer")
        player.points = 400  # Novice threshold

        leveled_up = player.level_up()

        self.assertTrue(leveled_up)
        self.assertEqual(player.level, "Novice")

    def test_level_up_updates_stats_on_level_change(self):
        """Test level_up updates stats when level changes."""
        player = Player("TestPlayer")
        player.points = 800  # Acolyte threshold

        player.level_up()

        self.assertEqual(player.stamina, levels[800]["stamina"])
        self.assertEqual(player.max_stamina, levels[800]["stamina"])
        self.assertEqual(player.strength, levels[800]["strength"])

    def test_level_up_returns_false_when_no_level_change(self):
        """Test level_up returns False when level doesn't change."""
        player = Player("TestPlayer")
        player.points = 100  # Still Neophyte

        leveled_up = player.level_up()

        self.assertFalse(leveled_up)

    def test_level_up_handles_multiple_level_jumps(self):
        """Test level_up handles jumping multiple levels."""
        player = Player("TestPlayer")
        player.points = 3200  # Magister threshold (skipping 3 levels)

        leveled_up = player.level_up()

        self.assertTrue(leveled_up)
        self.assertEqual(player.level, "Magister")

    def test_level_up_sets_next_level_threshold(self):
        """Test level_up sets next_level_at correctly."""
        player = Player("TestPlayer")
        player.points = 400

        player.level_up()

        self.assertEqual(player.next_level_at, 800)

    def test_level_up_sets_next_level_to_minus_one_at_max(self):
        """Test level_up sets next_level_at to -1 at max level."""
        player = Player("TestPlayer")
        player.points = 102400  # Archmage

        player.level_up()

        self.assertEqual(player.next_level_at, -1)

    @patch("asyncio.create_task")
    def test_level_up_sends_notification_when_leveled_up(self, mock_create_task):
        """Test level_up sends notification when level increases."""
        player = Player("TestPlayer")
        player.points = 400
        mock_sio = AsyncMock()
        online_sessions = {"sid1": {"player": player}}

        player.level_up(sio=mock_sio, online_sessions=online_sessions)

        mock_create_task.assert_called_once()


class PlayerAddPointsTest(unittest.TestCase):
    """Test Player.add_points functionality."""

    def test_add_points_increases_player_points(self):
        """Test add_points increases player's points."""
        player = Player("TestPlayer")

        leveled_up, notification = player.add_points(100)

        self.assertEqual(player.points, 100)

    def test_add_points_returns_notification_with_score(self):
        """Test add_points returns notification with score."""
        player = Player("TestPlayer")

        leveled_up, notification = player.add_points(50)

        self.assertEqual(notification, "[50]")

    def test_add_points_triggers_level_up_when_threshold_reached(self):
        """Test add_points triggers level_up when threshold reached."""
        player = Player("TestPlayer")
        player.points = 350

        leveled_up, notification = player.add_points(50)

        self.assertTrue(leveled_up)
        self.assertEqual(player.level, "Novice")

    def test_add_points_returns_false_when_no_level_up(self):
        """Test add_points returns False when no level up occurs."""
        player = Player("TestPlayer")

        leveled_up, notification = player.add_points(50)

        self.assertFalse(leveled_up)

    @patch("asyncio.create_task")
    def test_add_points_sends_notification_when_send_notification_true(
        self, mock_create_task
    ):
        """Test add_points sends notification when send_notification=True."""
        player = Player("TestPlayer")
        mock_sio = AsyncMock()
        online_sessions = {"sid1": {"player": player}}

        player.add_points(
            50, sio=mock_sio, online_sessions=online_sessions, send_notification=True
        )

        self.assertTrue(mock_create_task.called)


class PlayerInventoryTest(unittest.TestCase):
    """Test Player inventory management."""

    def test_add_item_adds_item_to_inventory(self):
        """Test add_item adds item to inventory."""
        player = Player("TestPlayer")
        item = create_mock_item(name="sword", weight=5, takeable=True)

        success, message = player.add_item(item)

        self.assertTrue(success)
        self.assertIn(item, player.inventory)

    def test_add_item_rejects_non_takeable_items(self):
        """Test add_item rejects items that are not takeable."""
        player = Player("TestPlayer")
        item = create_mock_item(name="boulder", weight=1000)
        item.takeable = False  # Explicitly set takeable to False

        success, message = player.add_item(item)

        self.assertFalse(success)
        self.assertIn("ridiculous", message)

    def test_add_item_respects_number_capacity(self):
        """Test add_item respects carrying capacity number limit."""
        player = Player("TestPlayer")
        player.carrying_capacity_num = 2

        item1 = create_mock_item(name="item1", weight=1, takeable=True)
        item2 = create_mock_item(name="item2", weight=1, takeable=True)
        item3 = create_mock_item(name="item3", weight=1, takeable=True)

        player.add_item(item1)
        player.add_item(item2)
        success, message = player.add_item(item3)

        self.assertFalse(success)
        self.assertIn("too many", message)

    def test_add_item_respects_weight_capacity(self):
        """Test add_item respects weight capacity based on strength."""
        player = Player("TestPlayer")
        player.strength = 10

        heavy_item = create_mock_item(name="anvil", weight=15, takeable=True)

        success, message = player.add_item(heavy_item)

        self.assertFalse(success)
        self.assertIn("too heavy", message)

    def test_remove_item_removes_item_from_inventory(self):
        """Test remove_item removes item from inventory."""
        player = Player("TestPlayer")
        item = create_mock_item(name="sword", takeable=True)
        player.inventory.append(item)

        success, message = player.remove_item(item)

        self.assertTrue(success)
        self.assertNotIn(item, player.inventory)

    def test_remove_item_returns_false_when_item_not_found(self):
        """Test remove_item returns False when item not in inventory."""
        player = Player("TestPlayer")
        item = create_mock_item(name="sword")

        success, message = player.remove_item(item)

        self.assertFalse(success)
        self.assertIn("not found", message)

    def test_total_inventory_weight_calculates_correctly(self):
        """Test total_inventory_weight calculates total weight."""
        player = Player("TestPlayer")
        item1 = create_mock_item(name="sword", weight=5, takeable=True)
        item2 = create_mock_item(name="shield", weight=10, takeable=True)
        player.inventory = [item1, item2]

        total = player.total_inventory_weight()

        self.assertEqual(total, 15)

    def test_drop_all_items_clears_inventory(self):
        """Test drop_all_items clears the inventory."""
        player = Player("TestPlayer")
        item1 = create_mock_item(name="sword")
        item2 = create_mock_item(name="shield")
        player.inventory = [item1, item2]

        dropped = player.drop_all_items()

        self.assertEqual(len(player.inventory), 0)
        self.assertEqual(len(dropped), 2)


class PlayerRoomManagementTest(unittest.TestCase):
    """Test Player room management."""

    def test_set_current_room_updates_room(self):
        """Test set_current_room updates current_room."""
        player = Player("TestPlayer")

        player.set_current_room("new_room")

        self.assertEqual(player.current_room, "new_room")

    def test_add_visited_adds_room_to_visited_set(self):
        """Test add_visited adds room to visited set."""
        player = Player("TestPlayer")

        player.add_visited("room1")
        player.add_visited("room2")

        self.assertIn("room1", player.visited)
        self.assertIn("room2", player.visited)
        self.assertEqual(len(player.visited), 2)


class PlayerSerializationTest(unittest.TestCase):
    """Test Player serialization."""

    def test_to_dict_includes_all_attributes(self):
        """Test to_dict includes all required attributes."""
        player = Player("TestPlayer", sex="F", email="test@example.com")
        player.points = 500

        data = player.to_dict()

        self.assertEqual(data["name"], "TestPlayer")
        self.assertEqual(data["sex"], "F")
        self.assertEqual(data["email"], "test@example.com")
        self.assertEqual(data["points"], 500)
        self.assertIn("inventory", data)
        self.assertIn("level", data)
        self.assertIn("current_room", data)

    def test_to_dict_serializes_inventory(self):
        """Test to_dict serializes inventory items."""
        player = Player("TestPlayer")
        item = create_mock_item(name="sword")
        item.to_dict = Mock(return_value={"name": "sword"})
        player.inventory.append(item)

        data = player.to_dict()

        self.assertEqual(len(data["inventory"]), 1)

    def test_from_dict_recreates_player(self):
        """Test from_dict recreates player from dictionary."""
        data = {
            "name": "TestPlayer",
            "sex": "F",
            "email": "test@example.com",
            "points": 500,
            "inventory": [],
            "level": "Novice",
            "current_room": "tavern",
        }

        player = Player.from_dict(data)

        self.assertEqual(player.name, "TestPlayer")
        self.assertEqual(player.sex, "F")
        self.assertEqual(player.points, 500)
        self.assertEqual(player.current_room, "tavern")

    def test_from_dict_restores_level_based_stats(self):
        """Test from_dict restores stats based on points."""
        data = {
            "name": "TestPlayer",
            "points": 800,  # Acolyte level
            "inventory": [],
            "level": "Acolyte",
            "current_room": "village_center",
        }

        player = Player.from_dict(data)

        self.assertEqual(player.max_stamina, levels[800]["stamina"])
        self.assertEqual(player.strength, levels[800]["strength"])

    def test_return_summary_provides_overview(self):
        """Test return_summary provides player overview."""
        player = Player("TestPlayer")
        player.points = 100

        summary = player.return_summary()

        self.assertEqual(summary["name"], "TestPlayer")
        self.assertEqual(summary["points"], 100)
        self.assertIn("stamina", summary)
        self.assertIn("inventory", summary)


class PlayerDeathRespawnTest(unittest.TestCase):
    """Test Player death and respawn behavior with score/points."""

    def test_player_serialization_preserves_points(self):
        """
        Test that Player.to_dict() and from_dict() preserve points.

        This tests the serialization/deserialization process to ensure
        points are correctly saved and restored. While this is basic
        functionality, it's important to verify for the death system.

        NOTE: In actual gameplay, if a player disconnects while awaiting
        respawn, their persona is DELETED by the disconnect handler in
        event_handlers.py, so they would never reach the "saved and loaded"
        state. This test only verifies the serialization logic itself.
        """
        # Create a player with some points/score
        player = Player("TestPlayer")
        player.points = 500
        player.level_up()
        original_points = player.points

        # Save/load cycle (tests serialization only)
        saved_data = player.to_dict()
        restored_player = Player.from_dict(saved_data)

        # RESULT: Points should be preserved through serialization
        self.assertEqual(restored_player.points, original_points)


class PlayerActivityTest(unittest.TestCase):
    """Test Player activity tracking."""

    def test_update_activity_updates_last_active(self):
        """Test update_activity updates last_active timestamp."""
        player = Player("TestPlayer")
        old_time = player.last_active

        import time

        time.sleep(0.01)  # Small delay
        player.update_activity()

        self.assertGreater(player.last_active, old_time)


class PlayerLightSourceTest(unittest.TestCase):
    """Test Player light source detection for darkness system."""

    def test_has_light_source_returns_false_with_no_items(self):
        """Test has_light_source returns False when inventory is empty."""
        player = Player("TestPlayer")

        self.assertFalse(player.has_light_source())

    def test_has_light_source_returns_false_with_non_light_items(self):
        """Test has_light_source returns False when no items emit light."""
        player = Player("TestPlayer")
        item1 = create_mock_item(name="sword", emits_light=False)
        item2 = create_mock_item(name="shield", emits_light=False)
        player.inventory = [item1, item2]

        self.assertFalse(player.has_light_source())

    def test_has_light_source_returns_true_with_light_emitting_item(self):
        """Test has_light_source returns True when player has a light source."""
        player = Player("TestPlayer")
        torch = create_mock_item(name="torch", emits_light=True)
        player.inventory = [torch]

        self.assertTrue(player.has_light_source())

    def test_has_light_source_finds_light_among_multiple_items(self):
        """Test has_light_source finds light source in mixed inventory."""
        player = Player("TestPlayer")
        sword = create_mock_item(name="sword", emits_light=False)
        torch = create_mock_item(name="torch", emits_light=True)
        shield = create_mock_item(name="shield", emits_light=False)
        player.inventory = [sword, torch, shield]

        self.assertTrue(player.has_light_source())


class PlayerEffectiveDexterityTest(unittest.TestCase):
    """Test Player effective dexterity calculation with darkness penalty."""

    def test_get_effective_dexterity_returns_full_dex_in_lit_room(self):
        """Test get_effective_dexterity returns full dexterity in lit room."""
        from models.Room import Room

        player = Player("TestPlayer")
        player.dexterity = 20
        room = Room("room1", "Lit Room", "A well-lit room", is_dark=False)
        online_sessions = {}
        game_state = Mock()

        effective_dex = player.get_effective_dexterity(
            room, online_sessions, game_state
        )

        self.assertEqual(effective_dex, 20)

    def test_get_effective_dexterity_applies_50_percent_penalty_in_dark_room_without_light(
        self,
    ):
        """Test get_effective_dexterity applies 50% penalty in dark room without light."""
        from models.Room import Room

        player = Player("TestPlayer")
        player.dexterity = 20
        room = Room("room1", "Dark Room", "A dark room", is_dark=True)
        online_sessions = {}
        game_state = Mock()
        game_state.get_room = Mock(return_value=room)
        room.get_items = Mock(return_value=[])

        effective_dex = player.get_effective_dexterity(
            room, online_sessions, game_state
        )

        self.assertEqual(effective_dex, 10)  # 50% penalty

    def test_get_effective_dexterity_returns_full_dex_in_dark_room_with_personal_light(
        self,
    ):
        """Test get_effective_dexterity returns full dexterity when player has light."""
        from models.Room import Room

        player = Player("TestPlayer")
        player.dexterity = 20
        player.current_room = "room1"  # Must match room's room_id
        torch = create_mock_item(name="torch", emits_light=True)
        player.inventory = [torch]
        room = Room("room1", "Dark Room", "A dark room", is_dark=True)
        room.get_items = Mock(return_value=[])  # No items on ground
        online_sessions = {
            "sid1": {"player": player}
        }  # Player with light is in the room
        game_state = Mock()

        effective_dex = player.get_effective_dexterity(
            room, online_sessions, game_state
        )

        self.assertEqual(effective_dex, 20)  # No penalty

    def test_get_effective_dexterity_returns_full_dex_when_other_player_has_light(
        self,
    ):
        """Test get_effective_dexterity returns full dexterity when another player has light."""
        from models.Room import Room

        player = Player("TestPlayer")
        player.dexterity = 20
        player.current_room = "room1"

        other_player = Player("OtherPlayer")
        other_player.current_room = "room1"
        torch = create_mock_item(name="torch", emits_light=True)
        other_player.inventory = [torch]

        room = Room("room1", "Dark Room", "A dark room", is_dark=True)
        online_sessions = {
            "sid1": {"player": player},
            "sid2": {"player": other_player},
        }
        game_state = Mock()

        effective_dex = player.get_effective_dexterity(
            room, online_sessions, game_state
        )

        self.assertEqual(effective_dex, 20)  # No penalty due to shared light

    def test_get_effective_dexterity_returns_full_dex_with_ground_light_source(self):
        """Test get_effective_dexterity returns full dexterity with light on ground."""
        from models.Room import Room

        player = Player("TestPlayer")
        player.dexterity = 20
        room = Room("room1", "Dark Room", "A dark room", is_dark=True)
        torch_on_ground = create_mock_item(name="torch", emits_light=True)
        room.items = [torch_on_ground]
        online_sessions = {}
        game_state = Mock()
        game_state.get_room = Mock(return_value=room)

        effective_dex = player.get_effective_dexterity(
            room, online_sessions, game_state
        )

        self.assertEqual(effective_dex, 20)  # No penalty due to ground light


if __name__ == "__main__":
    unittest.main()
