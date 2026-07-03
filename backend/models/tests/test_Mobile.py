"""
Comprehensive tests for Mobile model - CRITICAL.

Tests cover:
- Mobile initialization
- Combat behavior
- Movement/patrol
- Aggression mechanics
- Loot drops
- Damage/death
- Serialization
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.test_base import BaseModelTest
from tests.test_helpers import create_mock_item
from models.Mobile import Mobile


class MobileInitializationTest(BaseModelTest):
    """Test Mobile initialization."""

    def test___init___creates_mobile_with_name(self):
        """Test __init__ creates mobile with given name."""
        mob = Mobile("Orc", "orc_1", "A fierce orc")
        self.assertEqual(mob.name, "Orc")

    def test___init___sets_id(self):
        """Test __init__ sets unique ID."""
        mob = Mobile("Orc", "orc_1", "A fierce orc")
        self.assertEqual(mob.id, "orc_1")

    def test___init___sets_description(self):
        """Test __init__ sets description."""
        mob = Mobile("Orc", "orc_1", "A fierce orc")
        self.assertEqual(mob.description, "A fierce orc")

    def test___init___sets_combat_stats(self):
        """Test __init__ sets combat stats."""
        mob = Mobile(
            "Orc",
            "orc_1",
            "desc",
            strength=30,
            dexterity=25,
            max_stamina=150,
            damage=10,
        )
        self.assertEqual(mob.strength, 30)
        self.assertEqual(mob.dexterity, 25)
        self.assertEqual(mob.max_stamina, 150)
        self.assertEqual(mob.damage, 10)

    def test___init___sets_stamina_to_max(self):
        """Test __init__ sets stamina to max_stamina."""
        mob = Mobile("Orc", "orc_1", "desc", max_stamina=100)
        self.assertEqual(mob.stamina, 100)

    def test___init___sets_aggressive_flag(self):
        """Test __init__ sets aggressive flag."""
        mob = Mobile("Orc", "orc_1", "desc", aggressive=True)
        self.assertTrue(mob.aggressive)

    def test___init___sets_aggro_delay_range(self):
        """Test __init__ sets aggro delay range."""
        mob = Mobile("Orc", "orc_1", "desc", aggro_delay_min=5, aggro_delay_max=10)
        self.assertEqual(mob.aggro_delay_min, 5)
        self.assertEqual(mob.aggro_delay_max, 10)

    def test___init___sets_patrol_rooms(self):
        """Test __init__ sets patrol rooms."""
        rooms = ["room1", "room2", "room3"]
        mob = Mobile("Orc", "orc_1", "desc", patrol_rooms=rooms)
        self.assertEqual(mob.patrol_rooms, rooms)

    def test___init___sets_movement_interval(self):
        """Test __init__ sets movement interval."""
        mob = Mobile("Orc", "orc_1", "desc", movement_interval=15)
        self.assertEqual(mob.movement_interval, 15)

    def test___init___sets_loot_table(self):
        """Test __init__ sets loot table."""
        loot = [{"item": create_mock_item(), "chance": 0.5}]
        mob = Mobile("Orc", "orc_1", "desc", loot_table=loot)
        self.assertEqual(len(mob.loot_table), 1)

    def test___init___sets_instant_death(self):
        """Test __init__ sets instant_death flag."""
        mob = Mobile("Rabbit", "rabbit_1", "desc", instant_death=True)
        self.assertTrue(mob.instant_death)

    def test___init___sets_point_value(self):
        """Test __init__ sets point value."""
        mob = Mobile("Orc", "orc_1", "desc", point_value=50)
        self.assertEqual(mob.point_value, 50)

    def test___init___sets_current_room(self):
        """Test __init__ sets current room."""
        mob = Mobile("Orc", "orc_1", "desc", current_room="tavern")
        self.assertEqual(mob.current_room, "tavern")

    def test___init___sets_state_to_alive(self):
        """Test __init__ sets initial state to alive."""
        mob = Mobile("Orc", "orc_1", "desc")
        self.assertEqual(mob.state, "alive")

    def test___init___sets_not_takeable(self):
        """Test __init__ sets mob as not takeable."""
        mob = Mobile("Orc", "orc_1", "desc")
        self.assertFalse(mob.takeable)


class MobileAggroTest(unittest.TestCase):
    """Test Mobile aggression mechanics."""

    def test_initialize_aggro_delay_sets_counter(self):
        """Test initialize_aggro_delay sets aggro counter."""
        mob = Mobile("Orc", "orc_1", "desc", aggressive=True, aggro_delay_max=10)

        mob.initialize_aggro_delay()

        self.assertIsNotNone(mob.aggro_tick_counter)
        self.assertGreaterEqual(mob.aggro_tick_counter, 0)
        self.assertLessEqual(mob.aggro_tick_counter, 10)

    def test_initialize_aggro_delay_respects_min_max_range(self):
        """Test initialize_aggro_delay respects min/max range."""
        mob = Mobile(
            "Orc",
            "orc_1",
            "desc",
            aggressive=True,
            aggro_delay_min=5,
            aggro_delay_max=5,
        )

        mob.initialize_aggro_delay()

        self.assertEqual(mob.aggro_tick_counter, 5)

    def test_can_attack_player_returns_true_when_aggressive_and_ready(self):
        """Test can_attack_player returns True when aggressive and ready."""
        mob = Mobile("Orc", "orc_1", "desc", aggressive=True)
        mob.aggro_tick_counter = 0

        can_attack = mob.can_attack_player()

        self.assertTrue(can_attack)

    def test_can_attack_player_returns_false_when_not_aggressive(self):
        """Test can_attack_player returns False when not aggressive."""
        mob = Mobile("Orc", "orc_1", "desc", aggressive=False)
        mob.aggro_tick_counter = 0

        can_attack = mob.can_attack_player()

        self.assertFalse(can_attack)

    def test_can_attack_player_returns_false_when_aggro_delay_active(self):
        """Test can_attack_player returns False when aggro delay active."""
        mob = Mobile("Orc", "orc_1", "desc", aggressive=True)
        mob.aggro_tick_counter = 5

        can_attack = mob.can_attack_player()

        self.assertFalse(can_attack)

    def test_can_attack_player_returns_false_when_already_in_combat(self):
        """Test can_attack_player returns False when already in combat."""
        mob = Mobile("Orc", "orc_1", "desc", aggressive=True)
        mob.aggro_tick_counter = 0
        mob.target_player = Mock()

        can_attack = mob.can_attack_player()

        self.assertFalse(can_attack)

    def test_can_attack_player_returns_false_when_dead(self):
        """Test can_attack_player returns False when mob is dead."""
        mob = Mobile("Orc", "orc_1", "desc", aggressive=True)
        mob.state = "dead"
        mob.aggro_tick_counter = 0

        can_attack = mob.can_attack_player()

        self.assertFalse(can_attack)

    def test_tick_aggro_counter_decrements_counter(self):
        """Test tick_aggro_counter decrements the counter."""
        mob = Mobile("Orc", "orc_1", "desc")
        mob.aggro_tick_counter = 5

        mob.tick_aggro_counter()

        self.assertEqual(mob.aggro_tick_counter, 4)

    def test_tick_aggro_counter_stops_at_zero(self):
        """Test tick_aggro_counter stops at zero."""
        mob = Mobile("Orc", "orc_1", "desc")
        mob.aggro_tick_counter = 0

        mob.tick_aggro_counter()

        self.assertEqual(mob.aggro_tick_counter, 0)


class MobileMovementTest(unittest.TestCase):
    """Test Mobile movement mechanics."""

    def test_should_move_returns_true_when_interval_elapsed(self):
        """Test should_move returns True when movement interval elapsed."""
        mob = Mobile(
            "Orc",
            "orc_1",
            "desc",
            patrol_rooms=["room1", "room2"],
            movement_interval=10,
        )
        mob.last_move_tick = 0

        should_move = mob.should_move(10)

        self.assertTrue(should_move)

    def test_should_move_returns_false_when_interval_not_elapsed(self):
        """Test should_move returns False when interval not elapsed."""
        mob = Mobile(
            "Orc",
            "orc_1",
            "desc",
            patrol_rooms=["room1", "room2"],
            movement_interval=10,
        )
        mob.last_move_tick = 5

        should_move = mob.should_move(10)

        self.assertFalse(should_move)

    def test_should_move_returns_false_when_no_patrol_rooms(self):
        """Test should_move returns False when no patrol rooms."""
        mob = Mobile("Orc", "orc_1", "desc", patrol_rooms=[])

        should_move = mob.should_move(100)

        self.assertFalse(should_move)

    def test_should_move_returns_false_when_only_one_patrol_room(self):
        """Test should_move returns False when only one patrol room."""
        mob = Mobile("Orc", "orc_1", "desc", patrol_rooms=["room1"])

        should_move = mob.should_move(100)

        self.assertFalse(should_move)

    def test_should_move_returns_false_when_in_combat(self):
        """Test should_move returns False when in combat."""
        mob = Mobile("Orc", "orc_1", "desc", patrol_rooms=["room1", "room2"])
        mob.target_player = Mock()

        should_move = mob.should_move(100)

        self.assertFalse(should_move)

    def test_should_move_returns_false_when_dead(self):
        """Test should_move returns False when mob is dead."""
        mob = Mobile("Orc", "orc_1", "desc", patrol_rooms=["room1", "room2"])
        mob.state = "dead"

        should_move = mob.should_move(100)

        self.assertFalse(should_move)

    def test_choose_next_room_returns_next_in_patrol_list(self):
        """Test choose_next_room returns next room in patrol list."""
        rooms = ["room1", "room2", "room3"]
        mob = Mobile("Orc", "orc_1", "desc", patrol_rooms=rooms)
        mob.current_patrol_index = 0

        next_room = mob.choose_next_room()

        self.assertEqual(next_room, "room2")
        self.assertEqual(mob.current_patrol_index, 1)

    def test_choose_next_room_wraps_around_patrol_list(self):
        """Test choose_next_room wraps around to beginning."""
        rooms = ["room1", "room2", "room3"]
        mob = Mobile("Orc", "orc_1", "desc", patrol_rooms=rooms)
        mob.current_patrol_index = 2

        next_room = mob.choose_next_room()

        self.assertEqual(next_room, "room1")
        self.assertEqual(mob.current_patrol_index, 0)

    def test_move_to_room_updates_current_room(self):
        """Test move_to_room updates current room."""
        mob = Mobile("Orc", "orc_1", "desc", current_room="room1")

        mob.move_to_room("room2", 10)

        self.assertEqual(mob.current_room, "room2")

    def test_move_to_room_updates_last_move_tick(self):
        """Test move_to_room updates last move tick."""
        mob = Mobile("Orc", "orc_1", "desc")

        mob.move_to_room("room2", 15)

        self.assertEqual(mob.last_move_tick, 15)


class MobileCombatTest(unittest.TestCase):
    """Test Mobile combat mechanics."""

    def test_take_damage_reduces_stamina(self):
        """Test take_damage reduces stamina."""
        mob = Mobile("Orc", "orc_1", "desc", max_stamina=100)

        is_dead, remaining = mob.take_damage(30)

        self.assertFalse(is_dead)
        self.assertEqual(remaining, 70)
        self.assertEqual(mob.stamina, 70)

    def test_take_damage_kills_mob_when_stamina_zero(self):
        """Test take_damage kills mob when stamina reaches zero."""
        mob = Mobile("Orc", "orc_1", "desc", max_stamina=50)

        is_dead, remaining = mob.take_damage(50)

        self.assertTrue(is_dead)
        self.assertEqual(mob.stamina, 0)
        self.assertEqual(mob.state, "dead")

    def test_take_damage_prevents_negative_stamina(self):
        """Test take_damage prevents negative stamina."""
        mob = Mobile("Orc", "orc_1", "desc", max_stamina=50)

        mob.take_damage(100)

        self.assertEqual(mob.stamina, 0)

    def test_take_damage_instant_death_kills_immediately(self):
        """Test take_damage with instant_death kills immediately."""
        mob = Mobile("Rabbit", "rabbit_1", "desc", max_stamina=100, instant_death=True)

        is_dead, remaining = mob.take_damage(1)

        self.assertTrue(is_dead)
        self.assertEqual(mob.stamina, 0)
        self.assertEqual(mob.state, "dead")

    def test_take_damage_updates_description_when_dead(self):
        """Test take_damage updates description when mob dies."""
        mob = Mobile("Orc", "orc_1", "desc", max_stamina=50)

        mob.take_damage(50)

        self.assertIn("corpse", mob.description.lower())


class MobileLootTest(unittest.TestCase):
    """Test Mobile loot mechanics."""

    @patch("models.Mobile.random.random")
    def test_drop_loot_returns_items_based_on_chance(self, mock_random):
        """Test drop_loot returns items based on chance."""
        item = create_mock_item(name="gold coin")
        loot_table = [{"item": item, "chance": 0.5}]
        mob = Mobile("Orc", "orc_1", "desc", loot_table=loot_table)
        mock_random.return_value = 0.3  # Below 0.5 threshold

        dropped = mob.drop_loot()

        self.assertEqual(len(dropped), 1)
        self.assertEqual(dropped[0], item)

    @patch("models.Mobile.random.random")
    def test_drop_loot_respects_chance_threshold(self, mock_random):
        """Test drop_loot respects chance threshold."""
        item = create_mock_item(name="gold coin")
        loot_table = [{"item": item, "chance": 0.5}]
        mob = Mobile("Orc", "orc_1", "desc", loot_table=loot_table)
        mock_random.return_value = 0.7  # Above 0.5 threshold

        dropped = mob.drop_loot()

        self.assertEqual(len(dropped), 0)

    def test_drop_loot_returns_empty_list_when_no_loot_table(self):
        """Test drop_loot returns empty list when no loot table."""
        mob = Mobile("Orc", "orc_1", "desc", loot_table=[])

        dropped = mob.drop_loot()

        self.assertEqual(len(dropped), 0)


class MobileSerializationTest(unittest.TestCase):
    """Test Mobile serialization."""

    def test_to_dict_includes_mob_type(self):
        """Test to_dict includes mob_type identifier."""
        mob = Mobile("Orc", "orc_1", "desc")

        data = mob.to_dict()

        self.assertEqual(data["mob_type"], "mobile")

    def test_to_dict_includes_combat_stats(self):
        """Test to_dict includes combat stats."""
        mob = Mobile("Orc", "orc_1", "desc", strength=30, max_stamina=150)

        data = mob.to_dict()

        self.assertEqual(data["strength"], 30)
        self.assertEqual(data["max_stamina"], 150)

    def test_to_dict_includes_behavior_settings(self):
        """Test to_dict includes behavior settings."""
        mob = Mobile("Orc", "orc_1", "desc", aggressive=True, patrol_rooms=["r1", "r2"])

        data = mob.to_dict()

        self.assertTrue(data["aggressive"])
        self.assertEqual(data["patrol_rooms"], ["r1", "r2"])

    def test_is_mob_returns_true(self):
        """Test is_mob returns True."""
        mob = Mobile("Orc", "orc_1", "desc")

        self.assertTrue(mob.is_mob())


class MobileTacticalInitializationTest(unittest.TestCase):
    """Test Mobile initialization of tactical-combat attributes."""

    def test___init___defaults_magic_to_zero(self):
        """Test __init__ defaults magic to 0."""
        mob = Mobile("Orc", "orc_1", "desc")

        self.assertEqual(mob.magic, 0)

    def test___init___sets_magic_from_param(self):
        """Test __init__ sets magic from constructor parameter."""
        mob = Mobile("Orc", "orc_1", "desc", magic=40)

        self.assertEqual(mob.magic, 40)

    def test___init___creates_empty_afflictions_dict(self):
        """Test __init__ creates an empty afflictions dict."""
        mob = Mobile("Orc", "orc_1", "desc")

        self.assertEqual(mob.afflictions, {})

    def test___init___defaults_abilities_to_empty_list(self):
        """Test __init__ defaults abilities to an empty list."""
        mob = Mobile("Orc", "orc_1", "desc")

        self.assertEqual(mob.abilities, [])

    def test___init___sets_abilities_from_param(self):
        """Test __init__ sets abilities from constructor parameter."""
        abilities = [{"spell": "blind", "chance": 0.5, "cooldown_ticks": 4}]

        mob = Mobile("Hag", "hag_1", "desc", abilities=abilities)

        self.assertEqual(mob.abilities, abilities)

    def test___init___creates_empty_ability_cooldowns(self):
        """Test __init__ creates an empty ability_cooldowns dict."""
        mob = Mobile("Orc", "orc_1", "desc")

        self.assertEqual(mob.ability_cooldowns, {})

    def test___init___defaults_death_broadcast_to_none(self):
        """Test __init__ defaults death_broadcast to None."""
        mob = Mobile("Orc", "orc_1", "desc")

        self.assertIsNone(mob.death_broadcast)

    def test___init___sets_death_broadcast_from_param(self):
        """Test __init__ sets death_broadcast from constructor parameter."""
        mob = Mobile(
            "Dragon", "dragon_1", "desc", death_broadcast="The dragon has fallen!"
        )

        self.assertEqual(mob.death_broadcast, "The dragon has fallen!")

    def test___init___defaults_spares_flagged_to_none(self):
        """Test __init__ defaults spares_flagged to None."""
        mob = Mobile("Wolf", "wolf_1", "desc")

        self.assertIsNone(mob.spares_flagged)

    def test___init___sets_spares_flagged_from_param(self):
        """Test __init__ sets spares_flagged from constructor parameter."""
        mob = Mobile("Wolf", "wolf_1", "desc", spares_flagged="nature_blessing")

        self.assertEqual(mob.spares_flagged, "nature_blessing")


class MobileCrippleMovementTest(unittest.TestCase):
    """Test should_move interaction with the cripple affliction."""

    def _make_patrolling_mob(self):
        """Build a mob that is otherwise eligible to move."""
        mob = Mobile(
            "Orc",
            "orc_1",
            "desc",
            patrol_rooms=["room1", "room2"],
            movement_interval=5,
        )
        mob.last_move_tick = 0
        return mob

    def test_should_move_returns_false_when_crippled(self):
        """Test should_move returns False while the mob is crippled."""
        # Arrange
        from services.affliction_service import apply_affliction_to_mob

        mob = self._make_patrolling_mob()
        apply_affliction_to_mob(mob, "cripple", 60, "Caster")

        # Act
        result = mob.should_move(current_tick=10)

        # Assert
        self.assertFalse(result)

    def test_should_move_returns_true_after_cripple_removed(self):
        """Test should_move returns True once the cripple is removed."""
        # Arrange
        from services.affliction_service import (
            apply_affliction_to_mob,
            remove_mob_affliction,
        )

        mob = self._make_patrolling_mob()
        apply_affliction_to_mob(mob, "cripple", 60, "Caster")
        remove_mob_affliction(mob, "cripple")

        # Act
        result = mob.should_move(current_tick=10)

        # Assert
        self.assertTrue(result)

    def test_should_move_returns_true_when_cripple_expired(self):
        """Test should_move returns True when the cripple has expired."""
        # Arrange
        import time

        mob = self._make_patrolling_mob()
        mob.afflictions["cripple"] = {
            "applied_at": time.time() - 120,
            "expires_at": time.time() - 60,
            "caster": "Caster",
        }

        # Act
        result = mob.should_move(current_tick=10)

        # Assert
        self.assertTrue(result)

    def test_should_move_returns_false_when_crippled_even_if_other_afflicted(self):
        """Test non-cripple afflictions do not block movement."""
        # Arrange
        from services.affliction_service import apply_affliction_to_mob

        mob = self._make_patrolling_mob()
        apply_affliction_to_mob(mob, "blind", 60, "Caster")

        # Act
        result = mob.should_move(current_tick=10)

        # Assert
        self.assertTrue(result)


class MobileTacticalSerializationTest(unittest.TestCase):
    """Test serialization round-trip of tactical-combat attributes."""

    def test_to_dict_includes_magic(self):
        """Test to_dict includes the magic stat."""
        mob = Mobile("Orc", "orc_1", "desc", magic=35)

        data = mob.to_dict()

        self.assertEqual(data["magic"], 35)

    def test_to_dict_includes_abilities(self):
        """Test to_dict includes the abilities list."""
        abilities = [{"spell": "blind", "chance": 0.25, "cooldown_ticks": 4}]
        mob = Mobile("Hag", "hag_1", "desc", abilities=abilities)

        data = mob.to_dict()

        self.assertEqual(data["abilities"], abilities)

    def test_to_dict_includes_death_broadcast_and_spares_flagged(self):
        """Test to_dict includes death_broadcast and spares_flagged."""
        mob = Mobile(
            "Dragon",
            "dragon_1",
            "desc",
            death_broadcast="The dragon has fallen!",
            spares_flagged="nature_blessing",
        )

        data = mob.to_dict()

        self.assertEqual(data["death_broadcast"], "The dragon has fallen!")
        self.assertEqual(data["spares_flagged"], "nature_blessing")

    def test_from_dict_round_trips_tactical_fields(self):
        """Test from_dict restores magic/abilities/death_broadcast/spares_flagged."""
        # Arrange
        abilities = [
            {
                "spell": "blind",
                "chance": 1.0,
                "cooldown_ticks": 4,
                "duration_seconds": 15,
                "message": "Hex!",
            }
        ]
        original = Mobile(
            "Hag",
            "hag_1",
            "desc",
            magic=40,
            abilities=abilities,
            death_broadcast="The hag shrieks her last!",
            spares_flagged="witch_charm",
        )

        # Act
        restored = Mobile.from_dict(original.to_dict())

        # Assert
        self.assertEqual(restored.magic, 40)
        self.assertEqual(restored.abilities, abilities)
        self.assertEqual(restored.death_broadcast, "The hag shrieks her last!")
        self.assertEqual(restored.spares_flagged, "witch_charm")

    def test_from_dict_defaults_tactical_fields_when_absent(self):
        """Test from_dict uses safe defaults when tactical keys are missing."""
        # Arrange - minimal legacy-style data
        data = {"name": "Orc", "id": "orc_1", "description": "desc"}

        # Act
        mob = Mobile.from_dict(data)

        # Assert
        self.assertEqual(mob.magic, 0)
        self.assertEqual(mob.abilities, [])
        self.assertIsNone(mob.death_broadcast)
        self.assertIsNone(mob.spares_flagged)


if __name__ == "__main__":
    unittest.main()
