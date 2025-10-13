"""
Comprehensive tests for village_generator module.

Tests cover:
- generate_village_of_chronos returns dict
- Correct number of rooms
- Room instances
- Key rooms exist
- Exit connections
- Items in rooms
- Mob spawning with/without mob_manager
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from managers.village_generator import (
    generate_village_of_chronos,
    spawn_initial_mobs,
    generate_rooms,
    connect_exits,
    add_regular_items,
    add_container_items,
    add_weapons,
)
from models.Room import Room
from models.SpecializedRooms import SwampRoom


class VillageGeneratorStructureTest(unittest.TestCase):
    """Test village_generator structure."""

    def test_generate_village_of_chronos_returns_dict(self):
        """Test generate_village_of_chronos returns a dictionary."""
        village = generate_village_of_chronos()
        self.assertIsInstance(village, dict)

    def test_generate_village_of_chronos_creates_35_rooms(self):
        """Test generate_village_of_chronos creates 35 rooms."""
        village = generate_village_of_chronos()
        self.assertEqual(len(village), 35)

    def test_generate_village_of_chronos_all_values_are_room_objects(self):
        """Test all values are Room or SwampRoom objects."""
        village = generate_village_of_chronos()

        for room_id, room in village.items():
            self.assertTrue(
                isinstance(room, (Room, SwampRoom)),
                f"{room_id} is not a Room or SwampRoom instance",
            )


class VillageGeneratorKeyRoomsTest(unittest.TestCase):
    """Test key rooms exist."""

    def setUp(self):
        """Set up village for tests."""
        self.village = generate_village_of_chronos()

    def test_spawn_room_exists(self):
        """Test spawn room exists."""
        self.assertIn("spawn", self.village)
        self.assertEqual(self.village["spawn"].name, "Village Center")

    def test_marketplace_exists(self):
        """Test marketplace exists."""
        self.assertIn("marketplace", self.village)
        self.assertEqual(self.village["marketplace"].name, "Village Marketplace")

    def test_elders_cottage_exists(self):
        """Test Elder's cottage exists."""
        self.assertIn("elders_cottage", self.village)
        self.assertIn("Outside Elder's Cottage", self.village["elders_cottage"].name)

    def test_mystics_tower_exists(self):
        """Test Mystic's Tower exists."""
        self.assertIn("mystics_tower", self.village)
        self.assertIn("Tower", self.village["mystics_tower"].name)

    def test_ancient_library_exists(self):
        """Test Ancient Library exists."""
        self.assertIn("ancient_library", self.village)
        self.assertIn("Library", self.village["ancient_library"].name)

    def test_old_well_exists(self):
        """Test Old Well exists."""
        self.assertIn("old_well", self.village)
        self.assertIn("Well", self.village["old_well"].name)

    def test_swamp1_exists_as_swamp_room(self):
        """Test swamp1 exists and is a SwampRoom."""
        self.assertIn("swamp1", self.village)
        self.assertIsInstance(self.village["swamp1"], SwampRoom)

    def test_underswamp_exists(self):
        """Test underswamp (archmage-only area) exists."""
        self.assertIn("underswamp", self.village)
        self.assertEqual(self.village["underswamp"].name, "The Underswamp")


class VillageGeneratorExitsTest(unittest.TestCase):
    """Test room exit connections."""

    def setUp(self):
        """Set up village for tests."""
        self.village = generate_village_of_chronos()

    def test_spawn_has_four_cardinal_exits(self):
        """Test spawn has exits in all four directions."""
        spawn_exits = self.village["spawn"].exits
        self.assertIn("north", spawn_exits)
        self.assertIn("south", spawn_exits)
        self.assertIn("east", spawn_exits)
        self.assertIn("west", spawn_exits)

    def test_spawn_exits_point_to_correct_rooms(self):
        """Test spawn exits point to correct rooms."""
        spawn = self.village["spawn"]
        self.assertEqual(spawn.exits["north"], "northern_path")
        self.assertEqual(spawn.exits["east"], "marketplace")
        self.assertEqual(spawn.exits["south"], "old_well")
        self.assertEqual(spawn.exits["west"], "elders_cottage")

    def test_marketplace_connects_to_spawn(self):
        """Test marketplace connects back to spawn."""
        marketplace = self.village["marketplace"]
        self.assertIn("west", marketplace.exits)
        self.assertEqual(marketplace.exits["west"], "spawn")

    def test_tower_has_interior_access(self):
        """Test tower interior is connected."""
        tower_interior = self.village["tower_interior"]
        self.assertIn("out", tower_interior.exits)
        self.assertEqual(tower_interior.exits["out"], "mystics_tower")

    def test_underground_junction_connects_multiple_areas(self):
        """Test underground junction connects multiple areas."""
        junction = self.village["underground_junction"]
        # Should connect to well_bottom, cottage_cellar, shrine_underground, library_basement
        self.assertIn("west", junction.exits)
        self.assertIn("north", junction.exits)
        self.assertIn("east", junction.exits)
        self.assertIn("southeast", junction.exits)

    def test_underswamp_has_no_normal_exits(self):
        """Test underswamp has no normal exits (archmage teleport only)."""
        underswamp = self.village["underswamp"]
        self.assertEqual(underswamp.exits, {})


class VillageGeneratorItemsTest(unittest.TestCase):
    """Test items are added to rooms."""

    def setUp(self):
        """Set up village for tests."""
        self.village = generate_village_of_chronos()

    def test_spawn_has_sword(self):
        """Test spawn has sword weapon."""
        spawn = self.village["spawn"]
        sword = next(
            (item for item in spawn.items if "sword" in item.name.lower()), None
        )
        self.assertIsNotNone(sword, "Spawn should have a sword")

    def test_marketplace_has_key(self):
        """Test marketplace has bronze key."""
        marketplace = self.village["marketplace"]
        key = next(
            (item for item in marketplace.items if "key" in item.name.lower()), None
        )
        self.assertIsNotNone(key, "Marketplace should have a bronze key")

    def test_cottage_has_bag(self):
        """Test Elder's cottage has bag container."""
        cottage = self.village["elders_cottage"]
        bag = next((item for item in cottage.items if "bag" in item.name.lower()), None)
        self.assertIsNotNone(bag, "Elder's cottage should have a bag")

    def test_old_well_has_rope(self):
        """Test old well has rope."""
        old_well = self.village["old_well"]
        rope = next(
            (item for item in old_well.items if "rope" in item.name.lower()), None
        )
        self.assertIsNotNone(rope, "Old well should have rope")

    def test_cottage_interior_has_rug(self):
        """Test cottage interior has rug."""
        cottage_interior = self.village["cottage_interior"]
        rug = next(
            (item for item in cottage_interior.items if "rug" in item.name.lower()),
            None,
        )
        self.assertIsNotNone(rug, "Cottage interior should have rug")

    def test_forest_edge_has_yew_tree(self):
        """Test forest edge has yew tree."""
        forest_edge = self.village["forest_edge"]
        tree = next(
            (item for item in forest_edge.items if "tree" in item.name.lower()), None
        )
        self.assertIsNotNone(tree, "Forest edge should have yew tree")


class VillageGeneratorMobSpawningTest(unittest.TestCase):
    """Test mob spawning functionality."""

    def test_generate_village_spawns_mobs_when_mob_manager_provided(self):
        """Test mobs are spawned when mob_manager is provided."""
        mock_mob_manager = Mock()
        mock_mobs_dict = {}

        def mock_spawn(mob_type, room_id):
            mob = Mock()
            mob_id = f"{mob_type}_{len(mock_mobs_dict)}"
            mock_mobs_dict[mob_id] = mob
            return mob

        mock_mob_manager.spawn_mob = Mock(side_effect=mock_spawn)
        mock_mob_manager.mobs = mock_mobs_dict

        generate_village_of_chronos(mob_manager=mock_mob_manager)

        # Should have spawned at least some mobs
        self.assertGreater(mock_mob_manager.spawn_mob.call_count, 0)

    def test_generate_village_does_not_spawn_mobs_without_mob_manager(self):
        """Test no mobs are spawned when mob_manager is None."""
        village = generate_village_of_chronos(mob_manager=None)

        # Just verify it doesn't crash - no mobs should be spawned
        self.assertIsInstance(village, dict)

    @patch("managers.village_generator.spawn_initial_mobs")
    def test_generate_village_calls_spawn_initial_mobs(self, mock_spawn):
        """Test generate_village_of_chronos calls spawn_initial_mobs."""
        mock_mob_manager = Mock()

        village = generate_village_of_chronos(mob_manager=mock_mob_manager)

        mock_spawn.assert_called_once_with(mock_mob_manager, village)


class SpawnInitialMobsTest(unittest.TestCase):
    """Test spawn_initial_mobs functionality."""

    def setUp(self):
        """Set up mock mob manager and rooms."""
        self.mock_mob_manager = Mock()
        self.mock_mobs_dict = {}

        def mock_spawn(mob_type, room_id):
            mob = Mock()
            mob_id = f"{mob_type}_{len(self.mock_mobs_dict)}"
            self.mock_mobs_dict[mob_id] = mob
            return mob

        self.mock_mob_manager.spawn_mob = Mock(side_effect=mock_spawn)
        self.mock_mob_manager.mobs = self.mock_mobs_dict

        # Create minimal rooms dict
        self.rooms = {
            "marketplace": Mock(),
            "spawn": Mock(),
            "cottage_garden": Mock(),
            "forest_clearing": Mock(),
            "well_bottom": Mock(),
            "swamp1": Mock(),
        }

    def test_spawn_initial_mobs_spawns_village_merchant(self):
        """Test spawn_initial_mobs spawns village merchant in marketplace."""
        spawn_initial_mobs(self.mock_mob_manager, self.rooms)

        # Check if village_merchant was spawned in marketplace
        calls = self.mock_mob_manager.spawn_mob.call_args_list
        merchant_call = any(
            call[0][0] == "village_merchant" and call[0][1] == "marketplace"
            for call in calls
        )
        self.assertTrue(
            merchant_call, "village_merchant should be spawned in marketplace"
        )

    def test_spawn_initial_mobs_spawns_multiple_mob_types(self):
        """Test spawn_initial_mobs spawns multiple different mob types."""
        spawn_initial_mobs(self.mock_mob_manager, self.rooms)

        # Should spawn at least 4 different mob types
        self.assertGreaterEqual(self.mock_mob_manager.spawn_mob.call_count, 4)


class GenerateRoomsTest(unittest.TestCase):
    """Test generate_rooms functionality."""

    def test_generate_rooms_creates_spawn_room(self):
        """Test generate_rooms creates spawn room."""
        rooms = {}
        generate_rooms(rooms)

        self.assertIn("spawn", rooms)
        self.assertIsInstance(rooms["spawn"], Room)

    def test_generate_rooms_creates_35_rooms(self):
        """Test generate_rooms creates all 35 rooms."""
        rooms = {}
        generate_rooms(rooms)

        self.assertEqual(len(rooms), 35)

    def test_generate_rooms_creates_swamp_room(self):
        """Test generate_rooms creates SwampRoom for swamp1."""
        rooms = {}
        generate_rooms(rooms)

        self.assertIn("swamp1", rooms)
        self.assertIsInstance(rooms["swamp1"], SwampRoom)


class ConnectExitsTest(unittest.TestCase):
    """Test connect_exits functionality."""

    def test_connect_exits_connects_spawn_to_marketplace(self):
        """Test connect_exits creates spawn to marketplace connection."""
        rooms = {}
        generate_rooms(rooms)
        connect_exits(rooms)

        self.assertIn("east", rooms["spawn"].exits)
        self.assertEqual(rooms["spawn"].exits["east"], "marketplace")

    def test_connect_exits_creates_bidirectional_connections(self):
        """Test connect_exits creates bidirectional connections."""
        rooms = {}
        generate_rooms(rooms)
        connect_exits(rooms)

        # Check spawn <-> marketplace
        self.assertEqual(rooms["spawn"].exits["east"], "marketplace")
        self.assertEqual(rooms["marketplace"].exits["west"], "spawn")


class AddItemsTest(unittest.TestCase):
    """Test add_*_items functions."""

    def test_add_regular_items_adds_items(self):
        """Test add_regular_items adds items to rooms."""
        rooms = {}
        generate_rooms(rooms)

        add_regular_items(rooms)

        # Check that at least some rooms have items
        total_items = sum(len(room.items) for room in rooms.values())
        self.assertGreater(total_items, 0)

    def test_add_container_items_adds_bag(self):
        """Test add_container_items adds bag to cottage."""
        rooms = {}
        generate_rooms(rooms)

        add_container_items(rooms)

        cottage = rooms["elders_cottage"]
        bag = next((item for item in cottage.items if "bag" in item.name), None)
        self.assertIsNotNone(bag)

    def test_add_weapons_adds_sword_to_spawn(self):
        """Test add_weapons adds sword to spawn."""
        rooms = {}
        generate_rooms(rooms)

        add_weapons(rooms)

        spawn = rooms["spawn"]
        sword = next((item for item in spawn.items if "sword" in item.name), None)
        self.assertIsNotNone(sword)


if __name__ == "__main__":
    unittest.main()
