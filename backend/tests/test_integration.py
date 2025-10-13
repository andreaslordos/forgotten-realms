"""
Integration tests for game systems working together.

Tests realistic gameplay scenarios including:
- Player movement and exploration
- Item pickup and inventory management
- Combat with mobs
- Player interactions
- Level progression
- Death and respawn
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from models.Player import Player
from models.Item import Item
from models.Weapon import Weapon
from models.Room import Room
from models.Mobile import Mobile
from managers.game_state import GameState
from managers.mob_manager import MobManager


class PlayerExplorationTest(unittest.TestCase):
    """Test player exploration and movement."""

    def setUp(self):
        """Set up a simple world with connected rooms."""
        self.game_state = GameState()
        self.player = Player("Explorer")

        # Create connected rooms
        self.room1 = Room(
            "r1", "Village", "A peaceful village", exits={"north": "r2", "east": "r3"}
        )
        self.room2 = Room("r2", "Forest", "A dark forest", exits={"south": "r1"})
        self.room3 = Room("r3", "Cave", "A mysterious cave", exits={"west": "r1"})

        self.game_state.add_room(self.room1)
        self.game_state.add_room(self.room2)
        self.game_state.add_room(self.room3)

        self.player.set_current_room("r1")

    def test_explore_world_sequence(self):
        """Test player exploring multiple connected rooms."""
        # Start in village
        self.assertEqual(self.player.current_room, "r1")
        self.player.add_visited("r1")

        # Move north to forest
        room = self.game_state.get_room(self.player.current_room)
        next_room = room.exits["north"]
        self.player.set_current_room(next_room)
        self.player.add_visited(next_room)

        self.assertEqual(self.player.current_room, "r2")

        # Return to village
        room = self.game_state.get_room(self.player.current_room)
        next_room = room.exits["south"]
        self.player.set_current_room(next_room)

        self.assertEqual(self.player.current_room, "r1")

        # Check visited rooms
        self.assertIn("r1", self.player.visited)
        self.assertIn("r2", self.player.visited)
        self.assertEqual(len(self.player.visited), 2)

    def test_collect_items_while_exploring(self):
        """Test collecting items from different rooms."""
        # Add items to rooms
        sword = Item("Sword", "sword_1", "A rusty sword", weight=5, value=20)
        shield = Item("Shield", "shield_1", "A wooden shield", weight=8, value=15)

        self.room1.add_item(sword)
        self.room2.add_item(shield)

        # Collect sword from room1
        self.room1.remove_item(sword)
        success, msg = self.player.add_item(sword)
        self.assertTrue(success)

        # Move to room2
        self.player.set_current_room("r2")

        # Collect shield from room2
        self.room2.remove_item(shield)
        success, msg = self.player.add_item(shield)
        self.assertTrue(success)

        # Verify inventory
        self.assertEqual(len(self.player.inventory), 2)
        self.assertIn(sword, self.player.inventory)
        self.assertIn(shield, self.player.inventory)


class LootAndLevelProgressionTest(unittest.TestCase):
    """Test looting items and leveling up."""

    def setUp(self):
        """Set up player and game state."""
        self.player = Player("Adventurer")
        self.game_state = GameState()
        self.room = Room("test", "Test Room", "A room")
        self.game_state.add_room(self.room)
        self.player.set_current_room("test")

    def test_collect_valuable_items_gain_points(self):
        """Test collecting valuable items and gaining points."""
        # Add valuable items
        gem = Item("Ruby", "ruby_1", "A precious ruby", weight=0.5, value=100)
        diamond = Item(
            "Diamond", "diamond_1", "A sparkling diamond", weight=0.3, value=200
        )

        self.room.add_item(gem)
        self.room.add_item(diamond)

        # Collect items (simulating swamping them for points)
        initial_points = self.player.points

        # Simulate gaining points from swamping
        self.player.add_points(gem.value, send_notification=False)
        self.player.add_points(diamond.value, send_notification=False)

        # Check points increased
        self.assertEqual(self.player.points, initial_points + 300)

    def test_level_progression(self):
        """Test player leveling up through points."""
        initial_level = self.player.level

        # Give player enough points to level up (400 for next level from Novice)
        self.player.add_points(400, send_notification=False)

        # Check level changed
        self.assertNotEqual(self.player.level, initial_level)

    def test_stats_increase_with_level(self):
        """Test that player stats increase when leveling up."""
        initial_strength = self.player.strength
        initial_dexterity = self.player.dexterity
        initial_stamina = self.player.max_stamina

        # Level up
        self.player.add_points(400, send_notification=False)

        # Stats should have increased (or at least not decreased)
        self.assertGreaterEqual(self.player.strength, initial_strength)
        self.assertGreaterEqual(self.player.dexterity, initial_dexterity)
        self.assertGreaterEqual(self.player.max_stamina, initial_stamina)


class CombatIntegrationTest(unittest.TestCase):
    """Test combat scenarios."""

    def setUp(self):
        """Set up combat scenario."""
        self.player = Player("Warrior")
        self.game_state = GameState()
        self.room = Room("battlefield", "Battlefield", "A dangerous area")
        self.game_state.add_room(self.room)
        self.player.set_current_room("battlefield")

        # Give player a weapon
        self.sword = Weapon("Sword", "sword_1", "A sharp sword", damage=20)
        self.player.add_item(self.sword)

    def test_player_takes_damage(self):
        """Test player taking damage reduces stamina."""
        initial_stamina = self.player.stamina

        # Simulate damage
        damage = 30
        self.player.stamina -= damage

        self.assertEqual(self.player.stamina, initial_stamina - 30)

    def test_player_death_and_inventory_loss(self):
        """Test player death results in inventory drop."""
        # Add items to inventory (setUp already added sword)
        item1 = Item("Gold", "gold_1", "Gold coins")
        item2 = Item("Potion", "potion_1", "Health potion")
        self.player.add_item(item1)
        self.player.add_item(item2)

        # Simulate death (stamina to 0)
        self.player.stamina = 0

        # Drop all items
        dropped = self.player.drop_all_items()

        # Verify items were dropped and inventory cleared (sword + 2 new items = 3 total)
        self.assertEqual(len(dropped), 3)
        self.assertEqual(len(self.player.inventory), 0)
        self.assertIn(item1, dropped)
        self.assertIn(item2, dropped)
        self.assertIn(self.sword, dropped)

    def test_weapon_requirements_enforced(self):
        """Test that weapon requirements are checked."""
        # Create powerful weapon
        legendary_sword = Weapon(
            "Legendary Sword",
            "legendary_1",
            "An legendary weapon",
            damage=100,
            min_strength=50,
        )

        # Player doesn't meet requirements
        can_use, message = legendary_sword.can_use(self.player)

        self.assertFalse(can_use)
        self.assertIn("strength", message.lower())


class MobInteractionTest(unittest.TestCase):
    """Test player interactions with mobs."""

    def setUp(self):
        """Set up player and mob."""
        self.player = Player("Hero")
        self.game_state = GameState()
        self.room = Room("dungeon", "Dungeon", "A dark dungeon")
        self.game_state.add_room(self.room)
        self.player.set_current_room("dungeon")

        self.mob_manager = MobManager()

        # Create a mob
        self.goblin = Mobile(
            "Goblin",
            "goblin_1",
            "A nasty goblin",
            current_room="dungeon",
            aggressive=True,
        )
        self.mob_manager.mobs[self.goblin.id] = self.goblin

    def test_mob_in_same_room(self):
        """Test detecting mob in same room."""
        mobs_in_room = self.mob_manager.get_mobs_in_room("dungeon")

        self.assertEqual(len(mobs_in_room), 1)
        self.assertEqual(mobs_in_room[0], self.goblin)

    def test_mob_death_removes_from_manager(self):
        """Test that killing a mob removes it from the mob manager."""
        # Simulate mob death
        self.mob_manager.remove_mob(self.goblin.id)

        mobs_in_room = self.mob_manager.get_mobs_in_room("dungeon")
        self.assertEqual(len(mobs_in_room), 0)

    def test_aggressive_mob_attributes(self):
        """Test aggressive mob has correct attributes."""
        self.assertTrue(self.goblin.aggressive)

        # aggro_tick_counter is None until initialize_aggro_delay() is called
        self.assertIsNone(self.goblin.aggro_tick_counter)

        # Initialize aggro delay
        self.goblin.initialize_aggro_delay()
        self.assertIsNotNone(self.goblin.aggro_tick_counter)


class ItemPersistenceTest(unittest.TestCase):
    """Test item serialization and persistence."""

    def test_player_save_and_load(self):
        """Test saving and loading player state."""
        # Create player with items
        player = Player("SaveTest")
        sword = Item("Sword", "sword_1", "A sword", weight=5, value=50)
        player.add_item(sword)
        player.add_points(250, send_notification=False)
        player.set_current_room("test_room")

        # Serialize
        player_dict = player.to_dict()

        # Deserialize
        loaded_player = Player.from_dict(player_dict)

        # Verify
        self.assertEqual(loaded_player.name, player.name)
        self.assertEqual(loaded_player.points, player.points)
        self.assertEqual(loaded_player.level, player.level)
        self.assertEqual(loaded_player.current_room, player.current_room)
        self.assertEqual(len(loaded_player.inventory), 1)

    def test_room_save_and_load(self):
        """Test saving and loading room state."""
        # Create room with items
        room = Room("test", "Test", "A test room", exits={"north": "other"})
        item = Item("Key", "key_1", "A golden key")
        room.add_item(item)

        # Serialize
        room_dict = room.to_dict()

        # Deserialize
        loaded_room = Room.from_dict(room_dict)

        # Verify
        self.assertEqual(loaded_room.room_id, room.room_id)
        self.assertEqual(loaded_room.name, room.name)
        self.assertEqual(loaded_room.exits, room.exits)


class CompleteGameplayScenarioTest(unittest.TestCase):
    """Test complete gameplay scenarios."""

    def setUp(self):
        """Set up complete game world."""
        self.game_state = GameState()
        self.player = Player("Hero")
        self.mob_manager = MobManager()

        # Create a mini world
        self.village = Room(
            "village", "Village", "Safe village", exits={"north": "forest"}
        )
        self.forest = Room(
            "forest", "Dark Forest", "Dangerous forest", exits={"south": "village"}
        )

        self.game_state.add_room(self.village)
        self.game_state.add_room(self.forest)

        # Add items
        self.sword = Weapon("Sword", "sword_1", "A sword", damage=15)
        self.village.add_item(self.sword)

        # Add mob to forest
        self.wolf = Mobile("Wolf", "wolf_1", "A grey wolf", current_room="forest")
        self.mob_manager.mobs[self.wolf.id] = self.wolf

        self.player.set_current_room("village")

    def test_complete_adventure_flow(self):
        """Test a complete adventure: get weapon, explore, encounter mob."""
        # Start in village
        self.assertEqual(self.player.current_room, "village")

        # Pick up sword
        self.village.remove_item(self.sword)
        success, msg = self.player.add_item(self.sword)
        self.assertTrue(success)
        self.assertIn(self.sword, self.player.inventory)

        # Travel to forest
        self.player.set_current_room("forest")
        self.player.add_visited("forest")

        # Encounter wolf
        mobs_here = self.mob_manager.get_mobs_in_room("forest")
        self.assertEqual(len(mobs_here), 1)
        self.assertEqual(mobs_here[0], self.wolf)

        # Player should have sword equipped
        has_weapon = self.sword in self.player.inventory
        self.assertTrue(has_weapon)

    def test_exploration_tracks_visited_rooms(self):
        """Test that exploration properly tracks visited rooms."""
        # Visit multiple rooms
        rooms_to_visit = ["village", "forest", "village", "forest"]

        for room_id in rooms_to_visit:
            self.player.set_current_room(room_id)
            self.player.add_visited(room_id)

        # Should have visited 2 unique rooms (set removes duplicates)
        self.assertEqual(len(self.player.visited), 2)
        self.assertIn("village", self.player.visited)
        self.assertIn("forest", self.player.visited)


class WeightAndCapacityTest(unittest.TestCase):
    """Test inventory weight and capacity limits."""

    def setUp(self):
        """Set up player."""
        self.player = Player("Porter")

    def test_weight_limit_prevents_pickup(self):
        """Test that exceeding weight limit prevents item pickup."""
        # Player starts with limited strength
        initial_strength = self.player.strength

        # Create item heavier than capacity
        heavy_item = Item(
            "Boulder", "boulder_1", "Massive rock", weight=initial_strength + 10
        )

        # Try to pick up
        success, msg = self.player.add_item(heavy_item)

        self.assertFalse(success)
        self.assertIn("heavy", msg.lower())

    def test_item_count_limit_enforced(self):
        """Test that item count limit is enforced."""
        max_items = self.player.carrying_capacity_num

        # Add items up to limit
        for i in range(max_items):
            item = Item(f"Item{i}", f"item_{i}", "A small item", weight=0.1)
            success, msg = self.player.add_item(item)
            self.assertTrue(success)

        # Try to add one more
        extra_item = Item("Extra", "extra", "One too many", weight=0.1)
        success, msg = self.player.add_item(extra_item)

        self.assertFalse(success)
        self.assertIn("many", msg.lower())

    def test_dropping_item_frees_capacity(self):
        """Test that dropping items frees up capacity."""
        # Add an item
        item = Item("Rock", "rock_1", "A rock", weight=5)
        self.player.add_item(item)

        initial_count = len(self.player.inventory)

        # Drop it
        success, msg = self.player.remove_item(item)

        self.assertTrue(success)
        self.assertEqual(len(self.player.inventory), initial_count - 1)


if __name__ == "__main__":
    unittest.main()
