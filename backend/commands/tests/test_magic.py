"""
Comprehensive tests for magic spell system.

Tests cover:
- Core spell mechanics (success, resistance, backfire calculations)
- Helper functions (level checks, duration generation)
- Affliction spell handlers
- Utility spell handlers
- Combat spell handlers
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from commands.magic import (
    calculate_success_chance,
    calculate_resistance_chance,
    should_backfire,
    determine_backfire_effect,
    roll_spell_success,
    roll_resistance,
    check_min_level,
    get_level_index,
    get_magic_sleep_duration,
    find_target_player_or_mob,
    SPELL_DEFINITIONS,
    LEVEL_NAMES,
    MAGIC_SLEEP_MIN_DURATION,
    MAGIC_SLEEP_MAX_DURATION,
    handle_spells,
    handle_cure,
    handle_where,
    handle_wish,
    handle_summon,
    handle_force,
    handle_change,
    handle_sleep_spell,
    handle_deafen,
    handle_blind,
    handle_dumb,
    handle_cripple,
    handle_fod,
)


class CalculateSuccessChanceTest(unittest.TestCase):
    """Test calculate_success_chance function."""

    def test_neophyte_has_zero_success(self):
        """Test Neophyte (magic=0) has 0% success."""
        result = calculate_success_chance(0, 10)
        self.assertEqual(result, 0)

    def test_archmage_has_full_success(self):
        """Test Archmage (magic=100) has capped 100% success."""
        result = calculate_success_chance(100, 10)
        self.assertEqual(result, 100)

    def test_mid_level_magic_scales_correctly(self):
        """Test magic=50 gives 5x multiplier."""
        result = calculate_success_chance(50, 10)
        self.assertEqual(result, 50)

    def test_success_caps_at_100(self):
        """Test success chance caps at 100%."""
        result = calculate_success_chance(100, 20)
        self.assertEqual(result, 100)

    def test_warlock_magic_60_with_base_4(self):
        """Test Warlock (magic=60) with 4% base spell."""
        result = calculate_success_chance(60, 4)
        self.assertEqual(result, 24)


class CalculateResistanceChanceTest(unittest.TestCase):
    """Test calculate_resistance_chance function."""

    def test_neophyte_has_zero_resistance(self):
        """Test Neophyte (magic=0) has 0% resistance."""
        result = calculate_resistance_chance(0)
        self.assertEqual(result, 0)

    def test_archmage_has_full_resistance(self):
        """Test Archmage (magic=100) has 100% resistance."""
        result = calculate_resistance_chance(100)
        self.assertEqual(result, 100)

    def test_mid_level_resistance(self):
        """Test magic=50 gives 50% resistance."""
        result = calculate_resistance_chance(50)
        self.assertEqual(result, 50)


class ShouldBackfireTest(unittest.TestCase):
    """Test should_backfire function."""

    def test_no_backfire_if_spell_doesnt_allow(self):
        """Test spells with backfire_on_failure=False never backfire."""
        spell_def = SPELL_DEFINITIONS["where"]
        self.assertFalse(spell_def["backfire_on_failure"])

        # Even with low magic, shouldn't backfire
        with patch("commands.magic.random.randint", return_value=1):
            result = should_backfire(0, spell_def)
            self.assertFalse(result)

    def test_backfire_possible_with_low_magic(self):
        """Test low magic has high backfire chance."""
        spell_def = SPELL_DEFINITIONS["sleep"]
        self.assertTrue(spell_def["backfire_on_failure"])

        # Force backfire roll to succeed
        with patch("commands.magic.random.randint", return_value=1):
            result = should_backfire(0, spell_def)
            self.assertTrue(result)

    def test_archmage_never_backfires(self):
        """Test Archmage (magic=100) never backfires."""
        spell_def = SPELL_DEFINITIONS["sleep"]

        # backfire_chance = 50 - (100/2) = 0
        with patch("commands.magic.random.randint", return_value=1):
            result = should_backfire(100, spell_def)
            self.assertFalse(result)


class DetermineBackfireEffectTest(unittest.TestCase):
    """Test determine_backfire_effect function."""

    def test_self_effect_possible_when_allowed(self):
        """Test spells with backfire_affects_self can return 'self'."""
        spell_def = SPELL_DEFINITIONS["change"]
        self.assertTrue(spell_def["backfire_affects_self"])

        with patch("commands.magic.random.random", return_value=0.3):
            result = determine_backfire_effect(spell_def)
            self.assertEqual(result, "self")

    def test_sleep_effect_when_self_not_chosen(self):
        """Test 'sleep' returned when random doesn't pick 'self'."""
        spell_def = SPELL_DEFINITIONS["change"]

        with patch("commands.magic.random.random", return_value=0.7):
            result = determine_backfire_effect(spell_def)
            self.assertEqual(result, "sleep")

    def test_sleep_only_when_self_not_allowed(self):
        """Test always returns 'sleep' when backfire_affects_self=False."""
        spell_def = SPELL_DEFINITIONS["summon"]
        self.assertFalse(spell_def["backfire_affects_self"])

        result = determine_backfire_effect(spell_def)
        self.assertEqual(result, "sleep")


class GetLevelIndexTest(unittest.TestCase):
    """Test get_level_index function."""

    def test_neophyte_is_index_0(self):
        """Test Neophyte returns index 0."""
        self.assertEqual(get_level_index("Neophyte"), 0)

    def test_archmage_is_index_9(self):
        """Test Archmage returns index 9."""
        self.assertEqual(get_level_index("Archmage"), 9)

    def test_warlock_is_index_6(self):
        """Test Warlock returns index 6."""
        self.assertEqual(get_level_index("Warlock"), 6)

    def test_unknown_level_returns_0(self):
        """Test unknown level returns 0."""
        self.assertEqual(get_level_index("UnknownLevel"), 0)


class CheckMinLevelTest(unittest.TestCase):
    """Test check_min_level function."""

    def setUp(self):
        """Set up test player mock."""
        self.player = Mock()

    def test_archmage_can_cast_all_spells(self):
        """Test Archmage can cast any spell."""
        self.player.level = "Archmage"

        for spell_def in SPELL_DEFINITIONS.values():
            self.assertTrue(check_min_level(self.player, spell_def))

    def test_neophyte_can_only_cast_wish(self):
        """Test Neophyte can only cast WISH (min_level=0)."""
        self.player.level = "Neophyte"

        for spell_name, spell_def in SPELL_DEFINITIONS.items():
            result = check_min_level(self.player, spell_def)
            if spell_name == "wish":
                self.assertTrue(result)
            elif spell_def["min_level"] == 0:
                self.assertTrue(result)
            else:
                self.assertFalse(result)

    def test_scholar_can_cast_cripple(self):
        """Test Scholar (level 3) can cast CRIPPLE (min_level=3)."""
        self.player.level = "Scholar"
        spell_def = SPELL_DEFINITIONS["cripple"]

        self.assertTrue(check_min_level(self.player, spell_def))


class GetMagicSleepDurationTest(unittest.TestCase):
    """Test get_magic_sleep_duration function."""

    def test_duration_within_bounds(self):
        """Test duration is within 5-10 seconds."""
        for _ in range(100):
            duration = get_magic_sleep_duration()
            self.assertGreaterEqual(duration, MAGIC_SLEEP_MIN_DURATION)
            self.assertLessEqual(duration, MAGIC_SLEEP_MAX_DURATION)

    def test_duration_is_integer(self):
        """Test duration returns integer."""
        duration = get_magic_sleep_duration()
        self.assertIsInstance(duration, int)


class HandleSpellsTest(unittest.IsolatedAsyncioTestCase):
    """Test handle_spells command."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Mock()
        self.player.level = "Warlock"
        self.player.magic = 60
        self.game_state = Mock()
        self.player_manager = Mock()
        self.online_sessions = {}
        self.sio = Mock()
        self.utils = Mock()

    async def test_spells_hides_fod_for_non_archmage(self):
        """Test FOD is hidden from non-Archmages."""
        self.player.level = "Warlock"

        result = await handle_spells(
            {},
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertNotIn("FOD", result)
        self.assertNotIn("Finger of Death", result)

    async def test_spells_shows_fod_for_archmage(self):
        """Test FOD is shown to Archmages."""
        self.player.level = "Archmage"
        self.player.magic = 100

        result = await handle_spells(
            {},
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("FOD", result)

    async def test_spells_shows_player_probability(self):
        """Test spells shows calculated probability."""
        result = await handle_spells(
            {},
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Warlock with magic=60 casting WHERE (base 6%) = 36%
        self.assertIn("36%", result)

    async def test_spells_shows_locked_for_high_level_spells(self):
        """Test spells shows 'requires X' for locked spells."""
        self.player.level = "Novice"
        self.player.magic = 10

        result = await handle_spells(
            {},
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # FORCE requires Acolyte
        self.assertIn("requires Acolyte", result)


class HandleCureTest(unittest.IsolatedAsyncioTestCase):
    """Test handle_cure spell."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Mock()
        self.player.name = "Caster"
        self.player.level = "Archmage"
        self.player.magic = 100

        self.game_state = Mock()
        self.player_manager = Mock()
        self.sio = Mock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()

    async def test_cure_self_when_no_target(self):
        """Test cure targets self when no target given."""
        player_sid = "caster_sid"
        self.online_sessions = {
            player_sid: {
                "player": self.player,
                "afflictions": {"blind": {"expires_at": 9999999999}},
            }
        }

        cmd = {"verb": "cure"}

        with patch("commands.magic.find_player_sid", return_value=player_sid):
            result = await handle_cure(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                self.online_sessions,
                self.sio,
                self.utils,
            )

        self.assertIn("cure", result.lower())

    async def test_cure_reports_no_afflictions(self):
        """Test cure reports when target has no afflictions."""
        player_sid = "caster_sid"
        self.online_sessions = {
            player_sid: {
                "player": self.player,
                "afflictions": {},
            }
        }

        cmd = {"verb": "cure"}

        with patch("commands.magic.find_player_sid", return_value=player_sid):
            result = await handle_cure(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                self.online_sessions,
                self.sio,
                self.utils,
            )

        self.assertIn("no afflictions", result.lower())


class HandleWhereTest(unittest.IsolatedAsyncioTestCase):
    """Test handle_where spell."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Mock()
        self.player.name = "Caster"
        self.player.level = "Sovereign"
        self.player.magic = 80
        self.player.current_room = "room1"

        self.target = Mock()
        self.target.name = "Target"
        self.target.current_room = "room2"

        self.room = Mock()
        self.room.name = "The Town Square"

        self.game_state = Mock()
        self.game_state.get_room = Mock(return_value=self.room)
        self.game_state.rooms = {}

        self.player_manager = Mock()
        self.sio = Mock()
        self.utils = Mock()
        self.utils.mob_manager = Mock()
        self.utils.mob_manager.mobs = {}

    async def test_where_finds_online_player(self):
        """Test WHERE locates online player."""
        online_sessions = {"target_sid": {"player": self.target}}

        cmd = {"verb": "where", "subject": "Target"}

        result = await handle_where(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("Target", result)
        self.assertIn("Town Square", result)

    async def test_where_sovereign_always_succeeds(self):
        """Test Sovereign has 100% success on WHERE."""
        self.player.level = "Sovereign"
        online_sessions = {"target_sid": {"player": self.target}}

        cmd = {"verb": "where", "subject": "Target"}

        # Should always succeed regardless of roll
        with patch("commands.magic.roll_spell_success", return_value=False):
            result = await handle_where(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                online_sessions,
                self.sio,
                self.utils,
            )

        self.assertIn("Target", result)

    async def test_where_returns_not_found(self):
        """Test WHERE returns message when target not found."""
        online_sessions = {}

        cmd = {"verb": "where", "subject": "Nobody"}

        result = await handle_where(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("cannot locate", result.lower())


class HandleWishTest(unittest.IsolatedAsyncioTestCase):
    """Test handle_wish spell."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Mock()
        self.player.name = "Wisher"
        self.player.level = "Neophyte"
        self.player.magic = 0

        self.archmage = Mock()
        self.archmage.name = "Archmage1"
        self.archmage.level = "Archmage"

        self.game_state = Mock()
        self.player_manager = Mock()
        self.sio = Mock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()

    async def test_wish_always_succeeds(self):
        """Test WISH always succeeds (100% base chance)."""
        online_sessions = {"archmage_sid": {"player": self.archmage}}

        cmd = {"verb": "wish", "original": "wish for more gold"}

        with patch("builtins.open", unittest.mock.mock_open()):
            result = await handle_wish(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                online_sessions,
                self.sio,
                self.utils,
            )

        self.assertIn("heard", result.lower())

    async def test_wish_notifies_archmages(self):
        """Test WISH sends message to online Archmages."""
        online_sessions = {"archmage_sid": {"player": self.archmage}}

        cmd = {"verb": "wish", "original": "wish for wisdom"}

        with patch("builtins.open", unittest.mock.mock_open()):
            await handle_wish(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                online_sessions,
                self.sio,
                self.utils,
            )

        self.utils.send_message.assert_called()
        call_args = self.utils.send_message.call_args[0]
        self.assertIn("WISH", call_args[2])

    async def test_wish_requires_message(self):
        """Test WISH requires a message."""
        cmd = {"verb": "wish", "original": "wish"}

        result = await handle_wish(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            {},
            self.sio,
            self.utils,
        )

        self.assertIn("what do you wish", result.lower())


class SpellDefinitionsTest(unittest.TestCase):
    """Test spell definitions are valid."""

    def test_all_spells_have_required_fields(self):
        """Test all spell definitions have required fields."""
        required_fields = [
            "name",
            "base_chance",
            "min_level",
            "spell_type",
            "backfire_on_failure",
            "resistable",
            "requires_target",
            "help_text",
        ]

        for spell_name, spell_def in SPELL_DEFINITIONS.items():
            for field in required_fields:
                self.assertIn(field, spell_def, f"{spell_name} missing field {field}")

    def test_fod_is_archmage_only(self):
        """Test FOD requires Archmage level."""
        fod = SPELL_DEFINITIONS["fod"]
        self.assertEqual(fod["min_level"], 9)
        self.assertTrue(fod["archmage_only"])

    def test_wish_always_succeeds(self):
        """Test WISH has 100% base chance."""
        wish = SPELL_DEFINITIONS["wish"]
        self.assertEqual(wish["base_chance"], 100)

    def test_level_names_count(self):
        """Test there are exactly 10 level names."""
        self.assertEqual(len(LEVEL_NAMES), 10)


class RollSpellSuccessTest(unittest.TestCase):
    """Test roll_spell_success function."""

    def test_roll_success_with_high_chance(self):
        """Test roll succeeds with 100% chance."""
        with patch("commands.magic.random.randint", return_value=50):
            result = roll_spell_success(100, 10)  # 100% chance
            self.assertTrue(result)

    def test_roll_fails_with_zero_chance(self):
        """Test roll fails with 0% chance."""
        with patch("commands.magic.random.randint", return_value=1):
            result = roll_spell_success(0, 10)  # 0% chance
            self.assertFalse(result)

    def test_roll_success_when_roll_under_chance(self):
        """Test succeeds when roll is under chance."""
        with patch("commands.magic.random.randint", return_value=20):
            result = roll_spell_success(50, 10)  # 50% chance
            self.assertTrue(result)

    def test_roll_fails_when_roll_over_chance(self):
        """Test fails when roll is over chance."""
        with patch("commands.magic.random.randint", return_value=60):
            result = roll_spell_success(50, 10)  # 50% chance
            self.assertFalse(result)


class RollResistanceTest(unittest.TestCase):
    """Test roll_resistance function."""

    def test_roll_resistance_succeeds_with_high_magic(self):
        """Test resistance succeeds with high magic."""
        with patch("commands.magic.random.randint", return_value=50):
            result = roll_resistance(100)  # 100% resist
            self.assertTrue(result)

    def test_roll_resistance_fails_with_zero_magic(self):
        """Test resistance fails with zero magic."""
        with patch("commands.magic.random.randint", return_value=1):
            result = roll_resistance(0)  # 0% resist
            self.assertFalse(result)


class FindTargetPlayerOrMobTest(unittest.TestCase):
    """Test find_target_player_or_mob function."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Mock()
        self.player.current_room = "room1"
        self.game_state = Mock()
        self.utils = Mock()

    def test_returns_none_for_empty_name(self):
        """Test returns None for empty target name."""
        result = find_target_player_or_mob(
            "", self.player, self.game_state, {}, self.utils
        )
        self.assertEqual(result, (None, None, False))

    def test_finds_online_player(self):
        """Test finds online player by name."""
        target = Mock()
        target.name = "TargetPlayer"
        online_sessions = {"sid1": {"player": target}}

        result = find_target_player_or_mob(
            "Target", self.player, self.game_state, online_sessions, self.utils
        )

        self.assertEqual(result[0], target)
        self.assertEqual(result[1], "sid1")
        self.assertFalse(result[2])  # is_mob = False

    def test_finds_mob_in_room(self):
        """Test finds mob in same room."""
        mob = Mock()
        mob.name = "Goblin"
        mob_manager = Mock()
        mob_manager.get_mobs_in_room = Mock(return_value=[mob])
        self.utils.mob_manager = mob_manager

        result = find_target_player_or_mob(
            "Goblin", self.player, self.game_state, {}, self.utils
        )

        self.assertEqual(result[0], mob)
        self.assertIsNone(result[1])  # No sid for mobs
        self.assertTrue(result[2])  # is_mob = True

    def test_returns_none_when_not_found(self):
        """Test returns None when target not found."""
        self.utils.mob_manager = None

        result = find_target_player_or_mob(
            "Nobody", self.player, self.game_state, {}, self.utils
        )

        self.assertEqual(result, (None, None, False))


class HandleSummonTest(unittest.IsolatedAsyncioTestCase):
    """Test handle_summon spell."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Mock()
        self.player.name = "Caster"
        self.player.level = "Archmage"
        self.player.magic = 100
        self.player.current_room = "room1"

        self.target = Mock()
        self.target.name = "Target"
        self.target.level = "Novice"
        self.target.magic = 10
        self.target.current_room = "room2"
        self.target.inventory = []

        self.room = Mock()
        self.room.name = "Test Room"
        self.room.add_item = Mock()

        self.game_state = Mock()
        self.game_state.get_room = Mock(return_value=self.room)

        self.player_manager = Mock()
        self.sio = Mock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()
        self.utils.mob_manager = Mock()
        self.utils.mob_manager.get_mobs_in_room = Mock(return_value=[])

    async def test_summon_requires_target(self):
        """Test summon requires a target."""
        cmd = {"verb": "summon"}

        result = await handle_summon(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            {},
            self.sio,
            self.utils,
        )

        self.assertIn("whom", result.lower())

    async def test_summon_cannot_summon_self(self):
        """Test cannot summon yourself."""
        online_sessions = {"sid1": {"player": self.player}}
        cmd = {"verb": "summon", "subject": "Caster"}

        with patch(
            "commands.magic.find_player_by_name", return_value=(self.player, "sid1")
        ):
            result = await handle_summon(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                online_sessions,
                self.sio,
                self.utils,
            )

        self.assertIn("yourself", result.lower())

    async def test_summon_fails_for_low_level(self):
        """Test summon fails for low level caster."""
        self.player.level = "Neophyte"
        cmd = {"verb": "summon", "subject": "Target"}

        result = await handle_summon(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            {},
            self.sio,
            self.utils,
        )

        self.assertIn("must be at least", result.lower())

    async def test_summon_target_not_found(self):
        """Test summon when target not found."""
        cmd = {"verb": "summon", "subject": "Nobody"}

        with patch("commands.magic.find_player_by_name", return_value=(None, None)):
            result = await handle_summon(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                {},
                self.sio,
                self.utils,
            )

        self.assertIn("no one called", result.lower())

    async def test_summon_success_teleports_target(self):
        """Test successful summon teleports target."""
        online_sessions = {
            "caster_sid": {"player": self.player},
            "target_sid": {"player": self.target},
        }
        cmd = {"verb": "summon", "subject": "Target"}

        with patch(
            "commands.magic.find_player_by_name",
            return_value=(self.target, "target_sid"),
        ):
            with patch("commands.magic.find_player_sid", return_value="caster_sid"):
                with patch("commands.magic.roll_resistance", return_value=False):
                    with patch(
                        "services.notifications.broadcast_room", new_callable=AsyncMock
                    ):
                        with patch(
                            "commands.executor.build_look_description",
                            return_value="Room desc",
                        ):
                            result = await handle_summon(
                                cmd,
                                self.player,
                                self.game_state,
                                self.player_manager,
                                online_sessions,
                                self.sio,
                                self.utils,
                            )

        self.assertIn("summon", result.lower())
        self.target.set_current_room.assert_called_with("room1")

    async def test_summon_spell_fizzles(self):
        """Test summon spell can fizzle for non-archmage."""
        self.player.level = "Novice"
        self.player.magic = 10
        online_sessions = {"target_sid": {"player": self.target}}
        cmd = {"verb": "summon", "subject": "Target"}

        with patch(
            "commands.magic.find_player_by_name",
            return_value=(self.target, "target_sid"),
        ):
            with patch("commands.magic.find_player_sid", return_value="caster_sid"):
                with patch("commands.magic.roll_spell_success", return_value=False):
                    with patch("commands.magic.should_backfire", return_value=False):
                        result = await handle_summon(
                            cmd,
                            self.player,
                            self.game_state,
                            self.player_manager,
                            online_sessions,
                            self.sio,
                            self.utils,
                        )

        self.assertIn("fizzles", result.lower())

    async def test_summon_target_resists(self):
        """Test target can resist summon."""
        online_sessions = {"target_sid": {"player": self.target}}
        cmd = {"verb": "summon", "subject": "Target"}

        with patch(
            "commands.magic.find_player_by_name",
            return_value=(self.target, "target_sid"),
        ):
            with patch("commands.magic.find_player_sid", return_value="caster_sid"):
                with patch("commands.magic.roll_resistance", return_value=True):
                    result = await handle_summon(
                        cmd,
                        self.player,
                        self.game_state,
                        self.player_manager,
                        online_sessions,
                        self.sio,
                        self.utils,
                    )

        self.assertIn("resists", result.lower())


class HandleForceTest(unittest.IsolatedAsyncioTestCase):
    """Test handle_force spell."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Mock()
        self.player.name = "Caster"
        self.player.level = "Archmage"
        self.player.magic = 100

        self.target = Mock()
        self.target.name = "Target"
        self.target.magic = 10

        self.game_state = Mock()
        self.player_manager = Mock()
        self.sio = Mock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()

    async def test_force_requires_target_and_command(self):
        """Test force requires both target and command."""
        cmd = {"verb": "force", "original": "force"}

        result = await handle_force(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            {},
            self.sio,
            self.utils,
        )

        self.assertIn("whom", result.lower())

    async def test_force_forbids_dangerous_commands(self):
        """Test force forbids dangerous commands."""
        cmd = {"verb": "force", "original": "force target quit"}

        with patch(
            "commands.magic.find_player_by_name", return_value=(self.target, "sid1")
        ):
            result = await handle_force(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                {"sid1": {"player": self.target}},
                self.sio,
                self.utils,
            )

        self.assertIn("cannot force", result.lower())

    async def test_force_fails_for_low_level(self):
        """Test force fails for low level caster."""
        self.player.level = "Novice"
        cmd = {"verb": "force", "original": "force target look"}

        result = await handle_force(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            {},
            self.sio,
            self.utils,
        )

        self.assertIn("must be at least", result.lower())

    async def test_force_target_not_found(self):
        """Test force when target not found."""
        cmd = {"verb": "force", "original": "force nobody look"}

        with patch("commands.magic.find_player_by_name", return_value=(None, None)):
            result = await handle_force(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                {},
                self.sio,
                self.utils,
            )

        self.assertIn("no one called", result.lower())

    async def test_force_cannot_force_self(self):
        """Test cannot force yourself."""
        cmd = {"verb": "force", "original": "force caster look"}

        with patch(
            "commands.magic.find_player_by_name", return_value=(self.player, "sid1")
        ):
            result = await handle_force(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                {"sid1": {"player": self.player}},
                self.sio,
                self.utils,
            )

        self.assertIn("yourself", result.lower())

    async def test_force_success_queues_command(self):
        """Test successful force queues command on target."""
        online_sessions = {
            "target_sid": {"player": self.target, "command_queue": []},
        }
        cmd = {"verb": "force", "original": "force target look"}

        with patch(
            "commands.magic.find_player_by_name",
            return_value=(self.target, "target_sid"),
        ):
            with patch("commands.magic.find_player_sid", return_value="caster_sid"):
                with patch("commands.magic.roll_resistance", return_value=False):
                    result = await handle_force(
                        cmd,
                        self.player,
                        self.game_state,
                        self.player_manager,
                        online_sessions,
                        self.sio,
                        self.utils,
                    )

        self.assertIn("force", result.lower())
        self.assertIn("look", online_sessions["target_sid"]["command_queue"])

    async def test_force_spell_fizzles(self):
        """Test force spell can fizzle."""
        self.player.level = "Acolyte"
        self.player.magic = 20
        online_sessions = {"target_sid": {"player": self.target}}
        cmd = {"verb": "force", "original": "force target look"}

        with patch(
            "commands.magic.find_player_by_name",
            return_value=(self.target, "target_sid"),
        ):
            with patch("commands.magic.find_player_sid", return_value="caster_sid"):
                with patch("commands.magic.roll_spell_success", return_value=False):
                    with patch("commands.magic.should_backfire", return_value=False):
                        result = await handle_force(
                            cmd,
                            self.player,
                            self.game_state,
                            self.player_manager,
                            online_sessions,
                            self.sio,
                            self.utils,
                        )

        self.assertIn("fizzles", result.lower())

    async def test_force_target_resists(self):
        """Test target can resist force."""
        online_sessions = {"target_sid": {"player": self.target, "command_queue": []}}
        cmd = {"verb": "force", "original": "force target look"}

        with patch(
            "commands.magic.find_player_by_name",
            return_value=(self.target, "target_sid"),
        ):
            with patch("commands.magic.find_player_sid", return_value="caster_sid"):
                with patch("commands.magic.roll_resistance", return_value=True):
                    result = await handle_force(
                        cmd,
                        self.player,
                        self.game_state,
                        self.player_manager,
                        online_sessions,
                        self.sio,
                        self.utils,
                    )

        self.assertIn("resists", result.lower())


class HandleChangeTest(unittest.IsolatedAsyncioTestCase):
    """Test handle_change spell."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Mock()
        self.player.name = "Caster"
        self.player.level = "Archmage"
        self.player.magic = 100
        self.player.sex = "M"

        self.target = Mock()
        self.target.name = "Target"
        self.target.magic = 10
        self.target.sex = "M"

        self.game_state = Mock()
        self.player_manager = Mock()
        self.sio = Mock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()

    async def test_change_requires_target(self):
        """Test change requires a target."""
        cmd = {"verb": "change"}

        result = await handle_change(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            {},
            self.sio,
            self.utils,
        )

        self.assertIn("whom", result.lower())

    async def test_change_success_changes_sex(self):
        """Test successful change alters target's sex."""
        online_sessions = {"sid1": {"player": self.target}}
        cmd = {"verb": "change", "subject": "Target"}

        with patch(
            "commands.magic.find_player_by_name", return_value=(self.target, "sid1")
        ):
            with patch("commands.magic.roll_spell_success", return_value=True):
                with patch("commands.magic.roll_resistance", return_value=False):
                    result = await handle_change(
                        cmd,
                        self.player,
                        self.game_state,
                        self.player_manager,
                        online_sessions,
                        self.sio,
                        self.utils,
                    )

        self.assertEqual(self.target.sex, "F")
        self.assertIn("female", result.lower())

    async def test_change_target_not_found(self):
        """Test change when target not found."""
        cmd = {"verb": "change", "subject": "Nobody"}

        with patch("commands.magic.find_player_by_name", return_value=(None, None)):
            result = await handle_change(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                {},
                self.sio,
                self.utils,
            )

        self.assertIn("no one called", result.lower())

    async def test_change_spell_fizzles(self):
        """Test change spell can fizzle."""
        self.player.level = "Scholar"
        self.player.magic = 30
        online_sessions = {"target_sid": {"player": self.target}}
        cmd = {"verb": "change", "subject": "Target"}

        with patch(
            "commands.magic.find_player_by_name",
            return_value=(self.target, "target_sid"),
        ):
            with patch("commands.magic.find_player_sid", return_value="caster_sid"):
                with patch("commands.magic.roll_spell_success", return_value=False):
                    with patch("commands.magic.should_backfire", return_value=False):
                        result = await handle_change(
                            cmd,
                            self.player,
                            self.game_state,
                            self.player_manager,
                            online_sessions,
                            self.sio,
                            self.utils,
                        )

        self.assertIn("fizzles", result.lower())

    async def test_change_target_resists(self):
        """Test target can resist change."""
        online_sessions = {"target_sid": {"player": self.target}}
        cmd = {"verb": "change", "subject": "Target"}

        with patch(
            "commands.magic.find_player_by_name",
            return_value=(self.target, "target_sid"),
        ):
            with patch("commands.magic.find_player_sid", return_value="caster_sid"):
                with patch("commands.magic.roll_resistance", return_value=True):
                    result = await handle_change(
                        cmd,
                        self.player,
                        self.game_state,
                        self.player_manager,
                        online_sessions,
                        self.sio,
                        self.utils,
                    )

        self.assertIn("resists", result.lower())


class HandleSleepSpellTest(unittest.IsolatedAsyncioTestCase):
    """Test handle_sleep_spell function."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Mock()
        self.player.name = "Caster"
        self.player.level = "Archmage"
        self.player.magic = 100
        self.player.current_room = "room1"

        self.target = Mock()
        self.target.name = "Target"
        self.target.magic = 10
        self.target.current_room = "room1"

        self.game_state = Mock()
        self.player_manager = Mock()
        self.sio = Mock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()

    async def test_sleep_requires_target(self):
        """Test sleep spell requires a target."""
        cmd = {"verb": "sleep"}

        result = await handle_sleep_spell(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            {},
            self.sio,
            self.utils,
        )

        self.assertIn("whom", result.lower())

    async def test_sleep_fails_on_combat_target(self):
        """Test cannot sleep target in combat."""
        online_sessions = {"sid1": {"player": self.target}}
        cmd = {"verb": "sleep", "subject": "Target"}

        with patch(
            "commands.magic.find_player_by_name", return_value=(self.target, "sid1")
        ):
            with patch("commands.combat.is_in_combat", return_value=True):
                result = await handle_sleep_spell(
                    cmd,
                    self.player,
                    self.game_state,
                    self.player_manager,
                    online_sessions,
                    self.sio,
                    self.utils,
                )

        self.assertIn("combat", result.lower())


class HandleAfflictionSpellsTest(unittest.IsolatedAsyncioTestCase):
    """Test affliction spell handlers (deafen, blind, dumb, cripple)."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Mock()
        self.player.name = "Caster"
        self.player.level = "Archmage"
        self.player.magic = 100

        self.target = Mock()
        self.target.name = "Target"
        self.target.magic = 10

        self.game_state = Mock()
        self.player_manager = Mock()
        self.sio = Mock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()

    async def test_deafen_requires_target(self):
        """Test deafen requires a target."""
        cmd = {"verb": "deafen"}

        result = await handle_deafen(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            {},
            self.sio,
            self.utils,
        )

        self.assertIn("whom", result.lower())

    async def test_blind_requires_target(self):
        """Test blind requires a target."""
        cmd = {"verb": "blind"}

        result = await handle_blind(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            {},
            self.sio,
            self.utils,
        )

        self.assertIn("whom", result.lower())

    async def test_dumb_requires_target(self):
        """Test dumb requires a target."""
        cmd = {"verb": "dumb"}

        result = await handle_dumb(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            {},
            self.sio,
            self.utils,
        )

        self.assertIn("whom", result.lower())

    async def test_cripple_requires_target(self):
        """Test cripple requires a target."""
        cmd = {"verb": "cripple"}

        result = await handle_cripple(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            {},
            self.sio,
            self.utils,
        )

        self.assertIn("whom", result.lower())

    async def test_deafen_applies_affliction(self):
        """Test deafen applies deaf affliction."""
        online_sessions = {"sid1": {"player": self.target, "afflictions": {}}}
        cmd = {"verb": "deafen", "subject": "Target"}

        with patch(
            "commands.magic.find_player_by_name", return_value=(self.target, "sid1")
        ):
            with patch("commands.magic.find_player_sid", return_value="caster_sid"):
                result = await handle_deafen(
                    cmd,
                    self.player,
                    self.game_state,
                    self.player_manager,
                    online_sessions,
                    self.sio,
                    self.utils,
                )

        self.assertIn("deafen", result.lower())
        self.assertIn("deaf", online_sessions["sid1"]["afflictions"])


class HandleFodTest(unittest.IsolatedAsyncioTestCase):
    """Test handle_fod (Finger of Death) spell."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Mock()
        self.player.name = "Caster"
        self.player.level = "Archmage"
        self.player.magic = 100
        self.player.current_room = "room1"
        self.player.inventory = []

        self.target = Mock()
        self.target.name = "Target"
        self.target.level = "Novice"
        self.target.magic = 10
        self.target.current_room = "room1"
        self.target.inventory = []

        self.room = Mock()
        self.room.add_item = Mock()

        self.game_state = Mock()
        self.game_state.get_room = Mock(return_value=self.room)

        self.player_manager = Mock()
        self.sio = Mock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()
        self.utils.mob_manager = None

    async def test_fod_requires_target(self):
        """Test FOD requires a target."""
        cmd = {"verb": "fod"}

        result = await handle_fod(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            {},
            self.sio,
            self.utils,
        )

        self.assertIn("whom", result.lower())

    async def test_fod_kills_non_archmage_caster(self):
        """Test non-Archmage dies when casting FOD."""
        self.player.level = "Warlock"
        self.player.current_room = "room1"
        online_sessions = {"caster_sid": {"player": self.player}}
        cmd = {"verb": "fod", "subject": "Target"}

        with patch("commands.magic.find_player_sid", return_value="caster_sid"):
            with patch("commands.combat.active_combats", {}):
                with patch("commands.combat.end_combat"):
                    with patch(
                        "services.notifications.broadcast_room", new_callable=AsyncMock
                    ):
                        _result = await handle_fod(
                            cmd,
                            self.player,
                            self.game_state,
                            self.player_manager,
                            online_sessions,
                            self.sio,
                            self.utils,
                        )

        self.assertTrue(online_sessions["caster_sid"].get("combat_death"))

    async def test_fod_cannot_target_self(self):
        """Test cannot FOD yourself."""
        online_sessions = {"sid1": {"player": self.player}}
        cmd = {"verb": "fod", "subject": "Caster"}

        with patch(
            "commands.magic.find_target_player_or_mob",
            return_value=(self.player, "sid1", False),
        ):
            result = await handle_fod(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                online_sessions,
                self.sio,
                self.utils,
            )

        self.assertIn("yourself", result.lower())


class HandleSleepSpellSuccessTest(unittest.IsolatedAsyncioTestCase):
    """Test sleep spell success paths."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Mock()
        self.player.name = "Caster"
        self.player.level = "Archmage"
        self.player.magic = 100
        self.player.current_room = "room1"

        self.target = Mock()
        self.target.name = "Target"
        self.target.magic = 10
        self.target.current_room = "room1"

        self.game_state = Mock()
        self.player_manager = Mock()
        self.sio = Mock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()

    async def test_sleep_success_applies_affliction(self):
        """Test successful sleep spell applies magic_sleep affliction."""
        online_sessions = {
            "caster_sid": {"player": self.player},
            "target_sid": {"player": self.target},
        }
        cmd = {"verb": "sleep", "subject": "Target"}

        with patch(
            "commands.magic.find_player_by_name",
            return_value=(self.target, "target_sid"),
        ):
            with patch("commands.magic.find_player_sid", return_value="caster_sid"):
                with patch("commands.combat.is_in_combat", return_value=False):
                    with patch("commands.magic.roll_resistance", return_value=False):
                        with patch(
                            "services.notifications.broadcast_room",
                            new_callable=AsyncMock,
                        ):
                            result = await handle_sleep_spell(
                                cmd,
                                self.player,
                                self.game_state,
                                self.player_manager,
                                online_sessions,
                                self.sio,
                                self.utils,
                            )

        self.assertIn("sleep", result.lower())
        self.assertTrue(online_sessions["target_sid"].get("sleeping"))
        self.assertIn(
            "magic_sleep", online_sessions["target_sid"].get("afflictions", {})
        )

    async def test_sleep_spell_backfire(self):
        """Test sleep spell backfire puts caster to sleep."""
        self.player.level = "Novice"
        self.player.magic = 10
        online_sessions = {
            "caster_sid": {"player": self.player},
            "target_sid": {"player": self.target},
        }
        cmd = {"verb": "sleep", "subject": "Target"}

        with patch(
            "commands.magic.find_player_by_name",
            return_value=(self.target, "target_sid"),
        ):
            with patch("commands.magic.find_player_sid", return_value="caster_sid"):
                with patch("commands.combat.is_in_combat", return_value=False):
                    with patch("commands.magic.roll_spell_success", return_value=False):
                        with patch("commands.magic.should_backfire", return_value=True):
                            result = await handle_sleep_spell(
                                cmd,
                                self.player,
                                self.game_state,
                                self.player_manager,
                                online_sessions,
                                self.sio,
                                self.utils,
                            )

        self.assertIn("backfire", result.lower())
        self.assertTrue(online_sessions["caster_sid"].get("sleeping"))

    async def test_sleep_spell_resisted(self):
        """Test target resisting sleep spell."""
        online_sessions = {
            "caster_sid": {"player": self.player},
            "target_sid": {"player": self.target},
        }
        cmd = {"verb": "sleep", "subject": "Target"}

        with patch(
            "commands.magic.find_player_by_name",
            return_value=(self.target, "target_sid"),
        ):
            with patch("commands.magic.find_player_sid", return_value="caster_sid"):
                with patch("commands.combat.is_in_combat", return_value=False):
                    with patch("commands.magic.roll_resistance", return_value=True):
                        result = await handle_sleep_spell(
                            cmd,
                            self.player,
                            self.game_state,
                            self.player_manager,
                            online_sessions,
                            self.sio,
                            self.utils,
                        )

        self.assertIn("resist", result.lower())


class HandleAfflictionSpellSuccessTest(unittest.IsolatedAsyncioTestCase):
    """Test affliction spell success paths."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Mock()
        self.player.name = "Caster"
        self.player.level = "Archmage"
        self.player.magic = 100

        self.target = Mock()
        self.target.name = "Target"
        self.target.magic = 10

        self.game_state = Mock()
        self.player_manager = Mock()
        self.sio = Mock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()

    async def test_deafen_success_applies_affliction(self):
        """Test successful deafen applies deaf affliction."""
        online_sessions = {"target_sid": {"player": self.target}}
        cmd = {"verb": "deafen", "subject": "Target"}

        with patch(
            "commands.magic.find_player_by_name",
            return_value=(self.target, "target_sid"),
        ):
            with patch("commands.magic.roll_resistance", return_value=False):
                result = await handle_deafen(
                    cmd,
                    self.player,
                    self.game_state,
                    self.player_manager,
                    online_sessions,
                    self.sio,
                    self.utils,
                )

        self.assertIn("deaf", result.lower())
        self.assertIn("deaf", online_sessions["target_sid"].get("afflictions", {}))

    async def test_blind_success_applies_affliction(self):
        """Test successful blind applies blind affliction."""
        online_sessions = {"target_sid": {"player": self.target}}
        cmd = {"verb": "blind", "subject": "Target"}

        with patch(
            "commands.magic.find_player_by_name",
            return_value=(self.target, "target_sid"),
        ):
            with patch("commands.magic.roll_resistance", return_value=False):
                result = await handle_blind(
                    cmd,
                    self.player,
                    self.game_state,
                    self.player_manager,
                    online_sessions,
                    self.sio,
                    self.utils,
                )

        self.assertIn("blind", result.lower())

    async def test_affliction_spell_backfire_self(self):
        """Test affliction spell backfire affecting caster."""
        self.player.level = "Acolyte"  # Min level for deafen
        self.player.magic = 10
        online_sessions = {
            "caster_sid": {"player": self.player},
            "target_sid": {"player": self.target},
        }
        cmd = {"verb": "deafen", "subject": "Target"}

        with patch(
            "commands.magic.find_player_by_name",
            return_value=(self.target, "target_sid"),
        ):
            with patch("commands.magic.find_player_sid", return_value="caster_sid"):
                with patch("commands.magic.roll_spell_success", return_value=False):
                    with patch("commands.magic.should_backfire", return_value=True):
                        with patch(
                            "commands.magic.determine_backfire_effect",
                            return_value="self",
                        ):
                            result = await handle_deafen(
                                cmd,
                                self.player,
                                self.game_state,
                                self.player_manager,
                                online_sessions,
                                self.sio,
                                self.utils,
                            )

        self.assertIn("backfire", result.lower())

    async def test_affliction_spell_backfire_sleep(self):
        """Test affliction spell backfire causing sleep."""
        self.player.level = "Acolyte"  # Min level for deafen
        self.player.magic = 10
        online_sessions = {
            "caster_sid": {"player": self.player},
            "target_sid": {"player": self.target},
        }
        cmd = {"verb": "deafen", "subject": "Target"}

        with patch(
            "commands.magic.find_player_by_name",
            return_value=(self.target, "target_sid"),
        ):
            with patch("commands.magic.find_player_sid", return_value="caster_sid"):
                with patch("commands.magic.roll_spell_success", return_value=False):
                    with patch("commands.magic.should_backfire", return_value=True):
                        with patch(
                            "commands.magic.determine_backfire_effect",
                            return_value="sleep",
                        ):
                            result = await handle_deafen(
                                cmd,
                                self.player,
                                self.game_state,
                                self.player_manager,
                                online_sessions,
                                self.sio,
                                self.utils,
                            )

        self.assertIn("slumber", result.lower())
        self.assertTrue(online_sessions["caster_sid"].get("sleeping"))

    async def test_affliction_spell_resisted(self):
        """Test target resisting affliction spell."""
        online_sessions = {"target_sid": {"player": self.target}}
        cmd = {"verb": "deafen", "subject": "Target"}

        with patch(
            "commands.magic.find_player_by_name",
            return_value=(self.target, "target_sid"),
        ):
            with patch("commands.magic.roll_resistance", return_value=True):
                result = await handle_deafen(
                    cmd,
                    self.player,
                    self.game_state,
                    self.player_manager,
                    online_sessions,
                    self.sio,
                    self.utils,
                )

        self.assertIn("resist", result.lower())


class HandleChangeBackfireTest(unittest.IsolatedAsyncioTestCase):
    """Test change spell backfire paths."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Mock()
        self.player.name = "Caster"
        self.player.level = "Scholar"  # Min level for change spell
        self.player.magic = 10
        self.player.sex = "M"

        self.target = Mock()
        self.target.name = "Target"
        self.target.magic = 10
        self.target.sex = "M"

        self.game_state = Mock()
        self.player_manager = Mock()
        self.sio = Mock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()

    async def test_change_backfire_changes_caster_sex(self):
        """Test change backfire changes caster's sex."""
        online_sessions = {
            "caster_sid": {"player": self.player},
            "target_sid": {"player": self.target},
        }
        cmd = {"verb": "change", "subject": "Target"}

        with patch(
            "commands.magic.find_player_by_name",
            return_value=(self.target, "target_sid"),
        ):
            with patch("commands.magic.find_player_sid", return_value="caster_sid"):
                with patch("commands.magic.roll_spell_success", return_value=False):
                    with patch("commands.magic.should_backfire", return_value=True):
                        with patch(
                            "commands.magic.determine_backfire_effect",
                            return_value="self",
                        ):
                            result = await handle_change(
                                cmd,
                                self.player,
                                self.game_state,
                                self.player_manager,
                                online_sessions,
                                self.sio,
                                self.utils,
                            )

        self.assertIn("backfire", result.lower())
        self.assertEqual(self.player.sex, "F")

    async def test_change_backfire_sleep(self):
        """Test change backfire causes sleep."""
        online_sessions = {
            "caster_sid": {"player": self.player},
            "target_sid": {"player": self.target},
        }
        cmd = {"verb": "change", "subject": "Target"}

        with patch(
            "commands.magic.find_player_by_name",
            return_value=(self.target, "target_sid"),
        ):
            with patch("commands.magic.find_player_sid", return_value="caster_sid"):
                with patch("commands.magic.roll_spell_success", return_value=False):
                    with patch("commands.magic.should_backfire", return_value=True):
                        with patch(
                            "commands.magic.determine_backfire_effect",
                            return_value="sleep",
                        ):
                            result = await handle_change(
                                cmd,
                                self.player,
                                self.game_state,
                                self.player_manager,
                                online_sessions,
                                self.sio,
                                self.utils,
                            )

        self.assertIn("slumber", result.lower())
        self.assertTrue(online_sessions["caster_sid"].get("sleeping"))


class HandleForceSuccessTest(unittest.IsolatedAsyncioTestCase):
    """Test force spell success paths."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Mock()
        self.player.name = "Caster"
        self.player.level = "Archmage"
        self.player.magic = 100
        self.player.current_room = "room1"
        self.player.inventory = []

        self.target = Mock()
        self.target.name = "Target"
        self.target.magic = 10
        self.target.current_room = "room1"
        self.target.inventory = []

        self.game_state = Mock()
        self.player_manager = Mock()
        self.sio = Mock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()

    async def test_force_success_executes_command(self):
        """Test successful force executes the command."""
        online_sessions = {
            "caster_sid": {"player": self.player},
            "target_sid": {"player": self.target, "command_queue": []},
        }
        cmd = {"original": "force Target say hello"}

        with patch(
            "commands.magic.find_player_by_name",
            return_value=(self.target, "target_sid"),
        ):
            with patch("commands.magic.roll_resistance", return_value=False):
                result = await handle_force(
                    cmd,
                    self.player,
                    self.game_state,
                    self.player_manager,
                    online_sessions,
                    self.sio,
                    self.utils,
                )

        self.assertIn("force", result.lower())
        self.assertIn("say hello", online_sessions["target_sid"]["command_queue"])

    async def test_force_spell_backfire(self):
        """Test force spell backfire."""
        self.player.level = "Acolyte"  # Min level for force spell
        self.player.magic = 10
        online_sessions = {
            "caster_sid": {"player": self.player, "command_queue": []},
            "target_sid": {"player": self.target},
        }
        cmd = {"original": "force Target say hello"}

        with patch(
            "commands.magic.find_player_by_name",
            return_value=(self.target, "target_sid"),
        ):
            with patch("commands.magic.find_player_sid", return_value="caster_sid"):
                with patch("commands.magic.roll_spell_success", return_value=False):
                    with patch("commands.magic.should_backfire", return_value=True):
                        with patch(
                            "commands.magic.determine_backfire_effect",
                            return_value="self",
                        ):
                            result = await handle_force(
                                cmd,
                                self.player,
                                self.game_state,
                                self.player_manager,
                                online_sessions,
                                self.sio,
                                self.utils,
                            )

        self.assertIn("backfire", result.lower())

    async def test_force_spell_resisted(self):
        """Test target resisting force spell."""
        online_sessions = {"target_sid": {"player": self.target}}
        cmd = {"original": "force Target say hello"}

        with patch(
            "commands.magic.find_player_by_name",
            return_value=(self.target, "target_sid"),
        ):
            with patch("commands.magic.roll_resistance", return_value=True):
                result = await handle_force(
                    cmd,
                    self.player,
                    self.game_state,
                    self.player_manager,
                    online_sessions,
                    self.sio,
                    self.utils,
                )

        self.assertIn("resist", result.lower())


class HandleSummonSuccessPathTest(unittest.IsolatedAsyncioTestCase):
    """Test summon spell success and notification paths."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Mock()
        self.player.name = "Caster"
        self.player.level = "Archmage"
        self.player.magic = 100
        self.player.current_room = "room1"
        self.player.inventory = []

        self.target = Mock()
        self.target.name = "Target"
        self.target.magic = 10
        self.target.current_room = "room2"
        self.target.inventory = []

        self.game_state = Mock()
        self.player_manager = Mock()
        self.sio = Mock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()

    async def test_summon_notifies_target(self):
        """Test summon sends notification to summoned player."""
        online_sessions = {
            "caster_sid": {"player": self.player},
            "target_sid": {"player": self.target},
        }
        cmd = {"verb": "summon", "subject": "Target"}

        with patch(
            "commands.magic.find_player_by_name",
            return_value=(self.target, "target_sid"),
        ):
            with patch("commands.magic.find_player_sid", return_value="caster_sid"):
                with patch("commands.magic.roll_resistance", return_value=False):
                    with patch(
                        "services.notifications.broadcast_room", new_callable=AsyncMock
                    ):
                        with patch(
                            "commands.executor.build_look_description",
                            return_value="Room description",
                        ):
                            _result = await handle_summon(
                                cmd,
                                self.player,
                                self.game_state,
                                self.player_manager,
                                online_sessions,
                                self.sio,
                                self.utils,
                            )

        self.utils.send_message.assert_called()

    async def test_summon_changes_target_room(self):
        """Test summon teleports target to caster's room."""
        online_sessions = {
            "caster_sid": {"player": self.player},
            "target_sid": {"player": self.target},
        }
        cmd = {"verb": "summon", "subject": "Target"}

        with patch(
            "commands.magic.find_player_by_name",
            return_value=(self.target, "target_sid"),
        ):
            with patch("commands.magic.find_player_sid", return_value="caster_sid"):
                with patch("commands.magic.roll_resistance", return_value=False):
                    with patch(
                        "services.notifications.broadcast_room", new_callable=AsyncMock
                    ):
                        with patch(
                            "commands.executor.build_look_description",
                            return_value="Room desc",
                        ):
                            result = await handle_summon(
                                cmd,
                                self.player,
                                self.game_state,
                                self.player_manager,
                                online_sessions,
                                self.sio,
                                self.utils,
                            )

        self.target.set_current_room.assert_called_with("room1")
        self.assertIn("summon", result.lower())


class HandleWhereSuccessTest(unittest.IsolatedAsyncioTestCase):
    """Test where spell success paths."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Mock()
        self.player.name = "Caster"
        self.player.level = "Archmage"
        self.player.magic = 100
        self.player.current_room = "room1"

        self.target = Mock()
        self.target.name = "Target"
        self.target.current_room = "room2"

        self.game_state = Mock()
        room1 = Mock()
        room1.name = "The Marketplace"
        room2 = Mock()
        room2.name = "The Inn"
        self.game_state.get_room = Mock(
            side_effect=lambda r: room1 if r == "room1" else room2
        )

        self.player_manager = Mock()
        self.sio = Mock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()
        self.utils.mob_manager = Mock()
        self.utils.mob_manager.mobs = {}

    async def test_where_finds_player(self):
        """Test where spell finds player location."""
        self.game_state.rooms = {}  # Empty rooms dict
        online_sessions = {
            "caster_sid": {"player": self.player},
            "target_sid": {"player": self.target},
        }
        # Set inventory to empty list
        self.player.inventory = []
        self.target.inventory = []
        cmd = {"verb": "where", "subject": "Target"}

        result = await handle_where(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("inn", result.lower())

    async def test_where_finds_mob(self):
        """Test where spell finds mob location."""
        mock_mob = Mock()
        mock_mob.name = "Goblin"
        mock_mob.current_room = "room2"
        self.utils.mob_manager.mobs = {"mob1": mock_mob}

        self.game_state.rooms = {}  # Empty rooms dict
        self.player.inventory = []

        online_sessions = {"caster_sid": {"player": self.player}}
        cmd = {"verb": "where", "subject": "Goblin"}

        result = await handle_where(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("inn", result.lower())

    async def test_where_finds_item_in_room(self):
        """Test where spell finds item in a room."""
        mock_item = Mock()
        mock_item.name = "sword"

        room1 = Mock()
        room1.name = "The Marketplace"
        room1.get_items = Mock(return_value=[mock_item])

        self.game_state.rooms = {"room1": room1}
        self.game_state.get_room = Mock(return_value=room1)
        self.player.inventory = []

        online_sessions = {"caster_sid": {"player": self.player}}
        cmd = {"verb": "where", "subject": "sword"}

        result = await handle_where(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("marketplace", result.lower())


class HandleFodSuccessTest(unittest.IsolatedAsyncioTestCase):
    """Test FOD spell success paths."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Mock()
        self.player.name = "Caster"
        self.player.level = "Archmage"
        self.player.magic = 100
        self.player.current_room = "room1"
        self.player.inventory = []

        self.target = Mock()
        self.target.name = "Target"
        self.target.magic = 10
        self.target.current_room = "room1"
        self.target.inventory = []
        self.target.max_stamina = 100

        self.game_state = Mock()
        room = Mock()
        room.add_item = Mock()
        self.game_state.get_room = Mock(return_value=room)
        self.player_manager = Mock()
        self.sio = Mock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()
        self.utils.mob_manager = None

    async def test_fod_kills_player_target(self):
        """Test FOD kills a player target."""
        online_sessions = {
            "caster_sid": {"player": self.player},
            "target_sid": {"player": self.target},
        }
        cmd = {"verb": "fod", "subject": "Target"}

        with patch(
            "commands.magic.find_target_player_or_mob",
            return_value=(self.target, "target_sid", False),
        ):
            with patch("commands.combat.active_combats", {}):
                with patch("commands.combat.end_combat"):
                    with patch(
                        "services.notifications.broadcast_room", new_callable=AsyncMock
                    ):
                        result = await handle_fod(
                            cmd,
                            self.player,
                            self.game_state,
                            self.player_manager,
                            online_sessions,
                            self.sio,
                            self.utils,
                        )

        self.assertTrue(online_sessions["target_sid"].get("combat_death"))
        self.assertIn("finger", result.lower())

    async def test_fod_kills_mob_target(self):
        """Test FOD kills a mob target."""
        mock_mob = Mock()
        mock_mob.name = "Goblin"
        mock_mob.current_room = "room1"
        mock_mob.is_dead = False
        mock_mob.death_points = 100
        mock_mob.max_stamina = 50
        mock_mob.inventory = []
        mock_mob.point_value = 50

        mob_manager = Mock()
        mob_manager.get_mobs_in_room = Mock(return_value=[mock_mob])
        self.utils.mob_manager = mob_manager

        online_sessions = {"caster_sid": {"player": self.player}}
        cmd = {"verb": "fod", "subject": "Goblin"}

        with patch(
            "commands.magic.find_target_player_or_mob",
            return_value=(mock_mob, None, True),
        ):
            with patch("commands.combat.active_combats", {}):
                with patch("commands.combat.end_combat"):
                    with patch(
                        "commands.combat.handle_mob_defeat", new_callable=AsyncMock
                    ):
                        with patch(
                            "services.notifications.broadcast_room",
                            new_callable=AsyncMock,
                        ):
                            result = await handle_fod(
                                cmd,
                                self.player,
                                self.game_state,
                                self.player_manager,
                                online_sessions,
                                self.sio,
                                self.utils,
                            )

        # handle_mob_defeat is mocked, so we just check the result message
        self.assertIn("finger", result.lower())


class HandleCureOtherTest(unittest.IsolatedAsyncioTestCase):
    """Test cure spell on other players."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Mock()
        self.player.name = "Caster"
        self.player.level = "Archmage"
        self.player.magic = 100

        self.target = Mock()
        self.target.name = "Target"
        self.target.magic = 10

        self.game_state = Mock()
        self.player_manager = Mock()
        self.sio = Mock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()

    async def test_cure_other_player(self):
        """Test curing another player's afflictions."""
        online_sessions = {
            "caster_sid": {"player": self.player},
            "target_sid": {
                "player": self.target,
                "afflictions": {"blind": {"expires_at": 9999999999}},
            },
        }
        cmd = {"verb": "cure", "subject": "Target"}

        with patch(
            "commands.magic.find_player_by_name",
            return_value=(self.target, "target_sid"),
        ):
            result = await handle_cure(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                online_sessions,
                self.sio,
                self.utils,
            )

        self.assertIn("cure", result.lower())
        self.assertEqual(online_sessions["target_sid"]["afflictions"], {})


if __name__ == "__main__":
    unittest.main()
