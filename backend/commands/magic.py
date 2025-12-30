# backend/commands/magic.py

"""
Magic spell system based on MUD1 mechanics.

Spells use the formula: success_chance = base% * (magic / 10)
- Archmages (magic=100) cast with 100% success
- Targets can resist based on their magic stat
- Failed spells can backfire (put caster to sleep or affect caster)

Afflictions (DEAF, BLIND, DUMB, CRIPPLE) last 60 seconds by default.
"""

import logging
import os
import random
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, TypedDict

from commands.registry import command_registry
from commands.natural_language_parser import vocabulary_manager
from services.affliction_service import (
    apply_affliction,
    cure_all_afflictions,
    find_player_by_name,
    find_player_sid,
    has_affliction,
)
from services.notifications import broadcast_all, broadcast_item_drop

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ===== SPELL DEFINITIONS =====


class SpellType(Enum):
    """Types of spells based on their effects."""

    AFFLICTION = "affliction"
    UTILITY = "utility"
    OFFENSIVE = "offensive"
    CONTROL = "control"
    HEALING = "healing"


class SpellDefinition(TypedDict):
    """Type definition for spell configuration."""

    name: str
    base_chance: int
    min_level: int  # Level index 0-9 (Neophyte=0, Archmage=9)
    spell_type: SpellType
    affliction_type: Optional[str]
    duration_seconds: int
    archmage_only: bool
    backfire_on_failure: bool
    backfire_affects_self: bool
    resistable: bool
    requires_target: bool
    help_text: str


# Level names in order (index = level tier)
LEVEL_NAMES: List[str] = [
    "Neophyte",  # 0
    "Novice",  # 1
    "Acolyte",  # 2
    "Scholar",  # 3
    "Magister",  # 4
    "Archon",  # 5
    "Warlock",  # 6
    "Guardian",  # 7
    "Sovereign",  # 8
    "Archmage",  # 9
]


def get_level_index(level_name: str) -> int:
    """Get the numeric index for a level name."""
    try:
        return LEVEL_NAMES.index(level_name)
    except ValueError:
        return 0


SPELL_DEFINITIONS: Dict[str, SpellDefinition] = {
    "summon": {
        "name": "Summon",
        "base_chance": 4,
        "min_level": 1,  # Novice
        "spell_type": SpellType.CONTROL,
        "affliction_type": None,
        "duration_seconds": 0,
        "archmage_only": False,
        "backfire_on_failure": True,
        "backfire_affects_self": False,
        "resistable": True,
        "requires_target": True,
        "help_text": "Make target drop all items and teleport to you.",
    },
    "force": {
        "name": "Force",
        "base_chance": 4,
        "min_level": 2,  # Acolyte
        "spell_type": SpellType.CONTROL,
        "affliction_type": None,
        "duration_seconds": 0,
        "archmage_only": False,
        "backfire_on_failure": True,
        "backfire_affects_self": True,
        "resistable": True,
        "requires_target": True,
        "help_text": "Force target to execute a command.",
    },
    "where": {
        "name": "Where",
        "base_chance": 6,
        "min_level": 1,  # Novice
        "spell_type": SpellType.UTILITY,
        "affliction_type": None,
        "duration_seconds": 0,
        "archmage_only": False,
        "backfire_on_failure": False,
        "backfire_affects_self": False,
        "resistable": False,
        "requires_target": False,
        "help_text": "Locate an item or player. Sovereigns+ have 100% success.",
    },
    "change": {
        "name": "Change",
        "base_chance": 10,
        "min_level": 3,  # Scholar
        "spell_type": SpellType.CONTROL,
        "affliction_type": None,
        "duration_seconds": 0,
        "archmage_only": False,
        "backfire_on_failure": True,
        "backfire_affects_self": True,
        "resistable": True,
        "requires_target": True,
        "help_text": "Change target's sex.",
    },
    "sleep": {
        "name": "Sleep",
        "base_chance": 6,
        "min_level": 1,  # Novice
        "spell_type": SpellType.AFFLICTION,
        "affliction_type": "magic_sleep",
        "duration_seconds": 60,
        "archmage_only": False,
        "backfire_on_failure": True,
        "backfire_affects_self": True,
        "resistable": True,
        "requires_target": True,
        "help_text": "Put target to sleep for a duration.",
    },
    "wish": {
        "name": "Wish",
        "base_chance": 100,
        "min_level": 0,  # Neophyte (anyone)
        "spell_type": SpellType.UTILITY,
        "affliction_type": None,
        "duration_seconds": 0,
        "archmage_only": False,
        "backfire_on_failure": False,
        "backfire_affects_self": False,
        "resistable": False,
        "requires_target": False,
        "help_text": "Send a message to Archmages (logged).",
    },
    "deafen": {
        "name": "Deafen",
        "base_chance": 4,
        "min_level": 2,  # Acolyte
        "spell_type": SpellType.AFFLICTION,
        "affliction_type": "deaf",
        "duration_seconds": 60,
        "archmage_only": False,
        "backfire_on_failure": True,
        "backfire_affects_self": True,
        "resistable": True,
        "requires_target": True,
        "help_text": "Target cannot hear messages.",
    },
    "blind": {
        "name": "Blind",
        "base_chance": 4,
        "min_level": 2,  # Acolyte
        "spell_type": SpellType.AFFLICTION,
        "affliction_type": "blind",
        "duration_seconds": 60,
        "archmage_only": False,
        "backfire_on_failure": True,
        "backfire_affects_self": True,
        "resistable": True,
        "requires_target": True,
        "help_text": "Target cannot see room descriptions.",
    },
    "dumb": {
        "name": "Dumb",
        "base_chance": 4,
        "min_level": 2,  # Acolyte
        "spell_type": SpellType.AFFLICTION,
        "affliction_type": "dumb",
        "duration_seconds": 60,
        "archmage_only": False,
        "backfire_on_failure": True,
        "backfire_affects_self": True,
        "resistable": True,
        "requires_target": True,
        "help_text": "Target cannot speak.",
    },
    "cripple": {
        "name": "Cripple",
        "base_chance": 4,
        "min_level": 3,  # Scholar
        "spell_type": SpellType.AFFLICTION,
        "affliction_type": "cripple",
        "duration_seconds": 60,
        "archmage_only": False,
        "backfire_on_failure": True,
        "backfire_affects_self": True,
        "resistable": True,
        "requires_target": True,
        "help_text": "Target cannot move.",
    },
    "cure": {
        "name": "Cure",
        "base_chance": 8,
        "min_level": 1,  # Novice
        "spell_type": SpellType.HEALING,
        "affliction_type": None,
        "duration_seconds": 0,
        "archmage_only": False,
        "backfire_on_failure": False,
        "backfire_affects_self": False,
        "resistable": False,
        "requires_target": True,
        "help_text": "Remove all afflictions from target.",
    },
    "fod": {
        "name": "Finger of Death",
        "base_chance": 100,
        "min_level": 9,  # Archmage only
        "spell_type": SpellType.OFFENSIVE,
        "affliction_type": None,
        "duration_seconds": 0,
        "archmage_only": True,
        "backfire_on_failure": True,
        "backfire_affects_self": True,
        "resistable": False,
        "requires_target": True,
        "help_text": "Instant death. Non-Archmages die if they attempt it.",
    },
}

# Default affliction duration
DEFAULT_AFFLICTION_DURATION = 60

# Magic sleep duration range (seconds)
MAGIC_SLEEP_MIN_DURATION = 5
MAGIC_SLEEP_MAX_DURATION = 10


def get_magic_sleep_duration() -> int:
    """Get a random duration for magic sleep (5-10 seconds inclusive)."""
    return random.randint(MAGIC_SLEEP_MIN_DURATION, MAGIC_SLEEP_MAX_DURATION)


# ===== CORE SPELL MECHANICS =====


def calculate_success_chance(caster_magic: int, base_chance: int) -> int:
    """
    Calculate spell success chance.

    Formula: base_chance * (magic / 10)
    - Neophyte (magic=0): 0% success on most spells
    - Archmage (magic=100): base_chance * 10 = capped at 100%

    Args:
        caster_magic: Caster's magic stat (0-100)
        base_chance: Spell's base success percentage

    Returns:
        Success chance as percentage (0-100, capped)
    """
    multiplier = caster_magic / 10.0
    chance = int(base_chance * multiplier)
    return min(100, chance)


def calculate_resistance_chance(target_magic: int) -> int:
    """
    Calculate target's resistance chance.

    Formula: base_resistance * (magic / 10)
    Base resistance is 10%.

    Args:
        target_magic: Target's magic stat (0-100)

    Returns:
        Resistance chance as percentage (0-100)
    """
    base_resistance = 10
    multiplier = target_magic / 10.0
    return min(100, int(base_resistance * multiplier))


def should_backfire(caster_magic: int, spell_def: SpellDefinition) -> bool:
    """
    Determine if a failed spell backfires.

    Backfire chance: 50% - (magic / 2)
    - Neophyte: 50% backfire
    - Archmage: 0% backfire

    Args:
        caster_magic: Caster's magic stat
        spell_def: The spell definition

    Returns:
        True if spell backfires
    """
    if not spell_def["backfire_on_failure"]:
        return False

    backfire_chance = max(0, 50 - (caster_magic // 2))
    return random.randint(1, 100) <= backfire_chance


def determine_backfire_effect(spell_def: SpellDefinition) -> str:
    """
    Determine what happens on backfire.

    Options:
    1. Caster falls asleep (50% chance)
    2. Spell affects caster instead of target (50% chance, if applicable)

    Args:
        spell_def: The spell definition

    Returns:
        "sleep" or "self" indicating backfire type
    """
    if spell_def["backfire_affects_self"] and random.random() < 0.5:
        return "self"
    return "sleep"


def roll_spell_success(caster_magic: int, base_chance: int) -> bool:
    """
    Roll for spell success.

    Args:
        caster_magic: Caster's magic stat
        base_chance: Spell's base success percentage

    Returns:
        True if spell succeeds
    """
    success_chance = calculate_success_chance(caster_magic, base_chance)
    roll = random.randint(1, 100)
    return roll <= success_chance


def roll_resistance(target_magic: int) -> bool:
    """
    Roll for target resistance.

    Args:
        target_magic: Target's magic stat

    Returns:
        True if target resists
    """
    resist_chance = calculate_resistance_chance(target_magic)
    roll = random.randint(1, 100)
    return roll <= resist_chance


def check_min_level(player: Any, spell_def: SpellDefinition) -> bool:
    """
    Check if player meets minimum level requirement.

    Args:
        player: The player object
        spell_def: The spell definition

    Returns:
        True if player meets requirement
    """
    player_level_idx = get_level_index(player.level)
    return player_level_idx >= spell_def["min_level"]


# ===== HELPER FUNCTIONS =====


def find_target_player_or_mob(
    target_name: str,
    player: Any,
    game_state: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    utils: Any,
) -> Tuple[Optional[Any], Optional[str], bool]:
    """
    Find a target player or mob by name.

    Args:
        target_name: Name to search for
        player: The caster (to get current room)
        game_state: Game state
        online_sessions: Online sessions
        utils: Utils module with mob_manager

    Returns:
        Tuple of (target, target_sid, is_mob)
        - target: Player or Mobile object
        - target_sid: Session ID (only for players)
        - is_mob: True if target is a mob
    """
    if not target_name:
        return None, None, False

    target_lower = target_name.lower()

    # First check for online players
    for sid, session in online_sessions.items():
        other_player = session.get("player")
        if other_player and target_lower in other_player.name.lower():
            return other_player, sid, False

    # Check for mobs in the same room
    mob_manager = getattr(utils, "mob_manager", None)
    if mob_manager:
        mobs = mob_manager.get_mobs_in_room(player.current_room)
        for mob in mobs:
            if target_lower in mob.name.lower():
                return mob, None, True

    return None, None, False


# ===== SPELL HANDLERS =====


async def handle_summon(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    sio: Any,
    utils: Any,
) -> str:
    """
    SUMMON spell - Make target drop all items and teleport to caster.

    Syntax: summon <player>
    """
    spell_def = SPELL_DEFINITIONS["summon"]

    # Check minimum level
    if not check_min_level(player, spell_def):
        min_level_name = LEVEL_NAMES[spell_def["min_level"]]
        return f"You must be at least a {min_level_name} to cast {spell_def['name']}."

    target_name = cmd.get("subject")
    if not target_name:
        return "Summon whom?"

    # Find target player
    target, target_sid = find_player_by_name(target_name, online_sessions)
    if not target:
        return f"There is no one called '{target_name}' here."

    if target == player:
        return "You cannot summon yourself!"

    # Find caster's session
    caster_sid = find_player_sid(player, online_sessions)

    # Archmages always succeed
    if player.level == "Archmage":
        success = True
    else:
        success = roll_spell_success(player.magic, spell_def["base_chance"])

    if not success:
        # Check for backfire
        if should_backfire(player.magic, spell_def):
            effect = determine_backfire_effect(spell_def)
            if effect == "sleep" and caster_sid:
                session = online_sessions.get(caster_sid, {})
                apply_affliction(
                    session, "magic_sleep", get_magic_sleep_duration(), player.name
                )
                session["sleeping"] = True
                return "Your summon spell backfires! You fall into a magical slumber..."
        return "Your summon spell fizzles and fails."

    # Check target resistance
    if spell_def["resistable"] and roll_resistance(target.magic):
        if target_sid:
            await utils.send_message(
                sio, target_sid, f"You resist {player.name}'s summon spell!"
            )
        return f"{target.name} resists your summon!"

    # Success! Drop target's items in their current room
    target_room = game_state.get_room(target.current_room)
    old_room_id = target.current_room

    for item in list(target.inventory):
        target.remove_item(item)
        target_room.add_item(item)
        # Broadcast item drop to other players in the old room
        await broadcast_item_drop(old_room_id, target.name, item.name)

    # Teleport target to caster
    target.set_current_room(player.current_room)
    player_manager.save_players()

    # Notify old room
    from services.notifications import broadcast_room

    await broadcast_room(
        old_room_id,
        f"{target.name} vanishes in a flash of light!",
        exclude_player=[target.name],
    )

    # Notify new room (excluding caster and target)
    await broadcast_room(
        player.current_room,
        f"{target.name} appears in a flash of light!",
        exclude_player=[target.name, player.name],
    )

    # Show summoned player the room description
    if target_sid:
        from commands.executor import build_look_description

        await utils.send_message(
            sio,
            target_sid,
            f"You are summoned to {player.name}! All your items have been dropped.\n",
        )
        mob_manager = getattr(utils, "mob_manager", None)
        room_desc = build_look_description(
            target,
            game_state,
            online_sessions,
            look=True,
            mob_manager=mob_manager,
        )
        await utils.send_message(sio, target_sid, room_desc)

    # Build description of the summoned player for the caster
    # Format: "Name the Level is here, carrying X."
    inventory_desc = "nothing"
    if target.inventory:
        item_names = [item.name for item in target.inventory]
        inventory_desc = ", ".join(item_names)

    target_desc = (
        f"{target.name} the {target.level} is here, carrying {inventory_desc}."
    )

    return f"You summon {target.name}!\n{target.name} appears in a flash of light!\n{target_desc}"


async def handle_force(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    sio: Any,
    utils: Any,
) -> str:
    """
    FORCE spell - Make target execute a command.

    Syntax: force <player> <command>
    Example: force bob drop sword
    """
    spell_def = SPELL_DEFINITIONS["force"]

    # Check minimum level
    if not check_min_level(player, spell_def):
        min_level_name = LEVEL_NAMES[spell_def["min_level"]]
        return f"You must be at least a {min_level_name} to cast {spell_def['name']}."

    # Parse: force <target> <command>
    original = cmd.get("original", "")
    parts = original.split(maxsplit=2)

    if len(parts) < 3:
        return "Force whom to do what? (force <player> <command>)"

    target_name = parts[1]
    forced_command = parts[2]

    # Validate forced command - prevent dangerous commands
    forbidden = ["quit", "password", "force", "fod", "set", "reset", "summon"]
    for forbidden_cmd in forbidden:
        if forced_command.lower().startswith(forbidden_cmd):
            return f"You cannot force someone to '{forbidden_cmd}'!"

    # Find target
    target, target_sid = find_player_by_name(target_name, online_sessions)
    if not target:
        return f"There is no one called '{target_name}' here."

    if target == player:
        return "You cannot force yourself!"

    # Find caster's session
    caster_sid = find_player_sid(player, online_sessions)

    # Archmages always succeed
    if player.level == "Archmage":
        success = True
    else:
        success = roll_spell_success(player.magic, spell_def["base_chance"])

    if not success:
        if should_backfire(player.magic, spell_def):
            effect = determine_backfire_effect(spell_def)
            if effect == "self" and caster_sid:
                # Force affects caster instead
                session = online_sessions.get(caster_sid, {})
                if "command_queue" not in session:
                    session["command_queue"] = []
                session["command_queue"].append(forced_command)
                return f"Your force spell backfires! You feel compelled to '{forced_command}'!"
            elif effect == "sleep" and caster_sid:
                session = online_sessions.get(caster_sid, {})
                apply_affliction(
                    session, "magic_sleep", get_magic_sleep_duration(), player.name
                )
                session["sleeping"] = True
                return "Your force spell backfires! You fall into a magical slumber..."
        return "Your force spell fizzles and fails."

    # Check resistance
    if spell_def["resistable"] and roll_resistance(target.magic):
        if target_sid:
            await utils.send_message(
                sio, target_sid, f"You resist {player.name}'s force spell!"
            )
        return f"{target.name} resists your force!"

    # Success! Queue the command for target
    if target_sid:
        target_session = online_sessions.get(target_sid, {})
        if "command_queue" not in target_session:
            target_session["command_queue"] = []
        target_session["command_queue"].append(forced_command)
        await utils.send_message(
            sio, target_sid, f"You feel compelled to '{forced_command}'..."
        )

    return f"You force {target.name} to '{forced_command}'!"


async def handle_where(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    sio: Any,
    utils: Any,
) -> str:
    """
    WHERE spell - Locate an item or player.

    Syntax: where <item/player>
    Sovereigns and Archmages have 100% success.
    """
    spell_def = SPELL_DEFINITIONS["where"]

    # Check minimum level
    if not check_min_level(player, spell_def):
        min_level_name = LEVEL_NAMES[spell_def["min_level"]]
        return f"You must be at least a {min_level_name} to cast {spell_def['name']}."

    target = cmd.get("subject")
    if not target:
        return "Where what?"

    # Legends+ (Sovereign, Archmage) have 100% success
    legend_levels = ["Sovereign", "Archmage"]
    is_legend = player.level in legend_levels

    if not is_legend:
        if not roll_spell_success(player.magic, spell_def["base_chance"]):
            return "Your divination fails."

    target_lower = target.lower()

    # Search for player
    for sid, session in online_sessions.items():
        other_player = session.get("player")
        if other_player and target_lower in other_player.name.lower():
            room = game_state.get_room(other_player.current_room)
            room_name = room.name if room else "an unknown location"
            return f"{other_player.name} is at {room_name}."

    # Search for item in all rooms
    for room_id, room in game_state.rooms.items():
        for item in room.get_items(game_state):
            if target_lower in item.name.lower():
                return f"The {item.name} is at {room.name}."

    # Search player inventories
    for sid, session in online_sessions.items():
        other_player = session.get("player")
        if other_player:
            for item in other_player.inventory:
                if target_lower in item.name.lower():
                    return f"The {item.name} is being carried by {other_player.name}."

    # Search mobs
    mob_manager = getattr(utils, "mob_manager", None)
    if mob_manager:
        for mob in mob_manager.mobs.values():
            if target_lower in mob.name.lower():
                room = game_state.get_room(mob.current_room)
                room_name = room.name if room else "an unknown location"
                return f"{mob.name} is at {room_name}."

    return f"You cannot locate '{target}'."


async def handle_change(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    sio: Any,
    utils: Any,
) -> str:
    """
    CHANGE spell - Change target's sex.

    Syntax: change <player>
    """
    spell_def = SPELL_DEFINITIONS["change"]

    # Check minimum level
    if not check_min_level(player, spell_def):
        min_level_name = LEVEL_NAMES[spell_def["min_level"]]
        return f"You must be at least a {min_level_name} to cast {spell_def['name']}."

    target_name = cmd.get("subject")
    if not target_name:
        return "Change whom?"

    # Find target
    target, target_sid = find_player_by_name(target_name, online_sessions)
    if not target:
        return f"There is no one called '{target_name}' here."

    # Find caster's session
    caster_sid = find_player_sid(player, online_sessions)

    # Archmages always succeed
    if player.level == "Archmage":
        success = True
    else:
        success = roll_spell_success(player.magic, spell_def["base_chance"])

    if not success:
        if should_backfire(player.magic, spell_def):
            effect = determine_backfire_effect(spell_def)
            if effect == "self":
                # Change caster's sex instead
                old_sex = player.sex
                player.sex = "F" if player.sex == "M" else "M"
                player_manager.save_players()
                return f"Your change spell backfires! You transform from {old_sex} to {player.sex}!"
            elif effect == "sleep" and caster_sid:
                session = online_sessions.get(caster_sid, {})
                apply_affliction(
                    session, "magic_sleep", get_magic_sleep_duration(), player.name
                )
                session["sleeping"] = True
                return "Your change spell backfires! You fall into a magical slumber..."
        return "Your change spell fizzles and fails."

    # Check resistance (if target is not self)
    if target != player and spell_def["resistable"] and roll_resistance(target.magic):
        if target_sid:
            await utils.send_message(
                sio, target_sid, f"You resist {player.name}'s change spell!"
            )
        return f"{target.name} resists your change spell!"

    # Success! Change target's sex
    old_sex = target.sex
    target.sex = "F" if target.sex == "M" else "M"
    player_manager.save_players()

    if target_sid and target != player:
        sex_name = "female" if target.sex == "F" else "male"
        await utils.send_message(
            sio,
            target_sid,
            f"You feel a strange transformation... You are now {sex_name}!",
        )

    sex_name = "female" if target.sex == "F" else "male"
    return f"You change {target.name}'s sex to {sex_name}!"


async def handle_sleep_spell(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    sio: Any,
    utils: Any,
) -> str:
    """
    SLEEP spell - Put target to magical sleep.

    Syntax: sleep <player>
    Note: Different from rest sleep - uses magic_sleep affliction.
    """
    spell_def = SPELL_DEFINITIONS["sleep"]

    # Check minimum level
    if not check_min_level(player, spell_def):
        min_level_name = LEVEL_NAMES[spell_def["min_level"]]
        return f"You must be at least a {min_level_name} to cast {spell_def['name']}."

    target_name = cmd.get("subject")
    if not target_name:
        return "Put whom to sleep?"

    # Find target
    target, target_sid = find_player_by_name(target_name, online_sessions)
    if not target:
        return f"There is no one called '{target_name}' here."

    # Check if target is in combat
    from commands.combat import is_in_combat

    if is_in_combat(target.name):
        return f"{target.name} is too alert in combat to be put to sleep!"

    # Find caster's session
    caster_sid = find_player_sid(player, online_sessions)

    # Archmages always succeed
    if player.level == "Archmage":
        success = True
    else:
        success = roll_spell_success(player.magic, spell_def["base_chance"])

    if not success:
        if should_backfire(player.magic, spell_def):
            _effect = determine_backfire_effect(spell_def)
            if caster_sid:
                session = online_sessions.get(caster_sid, {})
                apply_affliction(
                    session, "magic_sleep", get_magic_sleep_duration(), player.name
                )
                session["sleeping"] = True
                return "Your sleep spell backfires! You fall into a magical slumber..."
        return "Your sleep spell fizzles and fails."

    # Check resistance
    if spell_def["resistable"] and roll_resistance(target.magic):
        if target_sid:
            await utils.send_message(
                sio, target_sid, f"You resist {player.name}'s sleep spell!"
            )
        return f"{target.name} resists your sleep spell!"

    # Success! Apply magic sleep
    if target_sid:
        target_session = online_sessions.get(target_sid, {})
        apply_affliction(
            target_session, "magic_sleep", get_magic_sleep_duration(), player.name
        )
        target_session["sleeping"] = True
        await utils.send_message(sio, target_sid, "You fall into a magical slumber...")

    # Notify room
    from services.notifications import broadcast_room

    await broadcast_room(
        target.current_room,
        f"{target.name} falls into a magical sleep!",
        exclude_player=[target.name, player.name],
    )

    return f"You put {target.name} to sleep!"


async def handle_wish(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    sio: Any,
    utils: Any,
) -> str:
    """
    WISH spell - Send a message to all Archmages and log to file.

    Syntax: wish <message>
    Always succeeds.
    """
    spell_def = SPELL_DEFINITIONS["wish"]

    # Check minimum level (should be 0, but check anyway)
    if not check_min_level(player, spell_def):
        min_level_name = LEVEL_NAMES[spell_def["min_level"]]
        return f"You must be at least a {min_level_name} to cast {spell_def['name']}."

    # Get the message - everything after "wish"
    original = cmd.get("original", "")
    parts = original.split(maxsplit=1)
    message = parts[1] if len(parts) > 1 else ""

    if not message:
        return "What do you wish?"

    # Log to file
    log_dir = os.path.join("storage")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "wishes.log")

    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] {player.name} ({player.level}): {message}\n"

    try:
        with open(log_path, "a") as f:
            f.write(log_entry)
    except IOError as e:
        logger.error(f"Failed to log wish: {e}")

    # Send to all online Archmages
    archmage_count = 0
    for sid, session in online_sessions.items():
        other_player = session.get("player")
        if other_player and other_player.level == "Archmage" and other_player != player:
            await utils.send_message(sio, sid, f"[WISH from {player.name}]: {message}")
            archmage_count += 1

    if archmage_count > 0:
        return f"Your wish has been heard by {archmage_count} Archmage(s)."
    return "Your wish has been heard by the powers that be."


async def handle_affliction_spell(
    spell_name: str,
    affliction_type: str,
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    sio: Any,
    utils: Any,
) -> str:
    """
    Generic handler for affliction spells (DEAFEN, BLIND, DUMB, CRIPPLE).

    Args:
        spell_name: Name of the spell
        affliction_type: Type of affliction to apply
        cmd: Command dict
        player: Caster
        ... other standard args
    """
    spell_def = SPELL_DEFINITIONS[spell_name]

    # Check minimum level
    if not check_min_level(player, spell_def):
        min_level_name = LEVEL_NAMES[spell_def["min_level"]]
        return f"You must be at least a {min_level_name} to cast {spell_def['name']}."

    target_name = cmd.get("subject")
    if not target_name:
        return f"{spell_def['name']} whom?"

    # Find target
    target, target_sid = find_player_by_name(target_name, online_sessions)
    if not target:
        return f"There is no one called '{target_name}' here."

    # Find caster's session
    caster_sid = find_player_sid(player, online_sessions)

    # Archmages always succeed
    if player.level == "Archmage":
        success = True
    else:
        success = roll_spell_success(player.magic, spell_def["base_chance"])

    if not success:
        if should_backfire(player.magic, spell_def):
            effect = determine_backfire_effect(spell_def)
            if effect == "self" and caster_sid:
                # Affliction affects caster
                session = online_sessions.get(caster_sid, {})
                apply_affliction(session, affliction_type, 60, player.name)
                return f"Your {spell_name} spell backfires! You are now {affliction_type}ed!"
            elif effect == "sleep" and caster_sid:
                session = online_sessions.get(caster_sid, {})
                apply_affliction(
                    session, "magic_sleep", get_magic_sleep_duration(), player.name
                )
                session["sleeping"] = True
                return f"Your {spell_name} spell backfires! You fall into a magical slumber..."
        return f"Your {spell_name} spell fizzles and fails."

    # Check resistance
    if spell_def["resistable"] and roll_resistance(target.magic):
        if target_sid:
            await utils.send_message(
                sio, target_sid, f"You resist {player.name}'s {spell_name} spell!"
            )
        return f"{target.name} resists your {spell_name} spell!"

    # Success! Apply affliction
    if target_sid:
        target_session = online_sessions.get(target_sid, {})
        apply_affliction(target_session, affliction_type, 60, player.name)

        affliction_messages = {
            "deaf": "You have been deafened! You cannot hear anything.",
            "blind": "You have been blinded! You cannot see anything.",
            "dumb": "You have been struck dumb! You cannot speak.",
            "cripple": "You have been crippled! You cannot move.",
        }
        msg = affliction_messages.get(
            affliction_type, f"You have been {affliction_type}ed by {player.name}!"
        )
        await utils.send_message(sio, target_sid, msg)

    return f"You {spell_name} {target.name}!"


async def handle_deafen(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    sio: Any,
    utils: Any,
) -> str:
    """DEAFEN spell - Make target unable to hear."""
    return await handle_affliction_spell(
        "deafen",
        "deaf",
        cmd,
        player,
        game_state,
        player_manager,
        online_sessions,
        sio,
        utils,
    )


async def handle_blind(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    sio: Any,
    utils: Any,
) -> str:
    """BLIND spell - Make target unable to see."""
    return await handle_affliction_spell(
        "blind",
        "blind",
        cmd,
        player,
        game_state,
        player_manager,
        online_sessions,
        sio,
        utils,
    )


async def handle_dumb(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    sio: Any,
    utils: Any,
) -> str:
    """DUMB spell - Make target unable to speak."""
    return await handle_affliction_spell(
        "dumb",
        "dumb",
        cmd,
        player,
        game_state,
        player_manager,
        online_sessions,
        sio,
        utils,
    )


async def handle_cripple(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    sio: Any,
    utils: Any,
) -> str:
    """CRIPPLE spell - Make target unable to move."""
    return await handle_affliction_spell(
        "cripple",
        "cripple",
        cmd,
        player,
        game_state,
        player_manager,
        online_sessions,
        sio,
        utils,
    )


async def handle_cure(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    sio: Any,
    utils: Any,
) -> str:
    """
    CURE spell - Remove all afflictions from target.

    Syntax: cure [player]
    If no target specified, cures self.
    """
    spell_def = SPELL_DEFINITIONS["cure"]

    # Check minimum level
    if not check_min_level(player, spell_def):
        min_level_name = LEVEL_NAMES[spell_def["min_level"]]
        return f"You must be at least a {min_level_name} to cast {spell_def['name']}."

    target_name = cmd.get("subject")

    # Default to self if no target
    if not target_name:
        target = player
        target_sid = find_player_sid(player, online_sessions)
    else:
        target, target_sid = find_player_by_name(target_name, online_sessions)

    if not target:
        return f"There is no one called '{target_name}' here."

    # Archmages always succeed
    if player.level == "Archmage":
        success = True
    else:
        success = roll_spell_success(player.magic, spell_def["base_chance"])

    if not success:
        return "Your cure spell fizzles and fails."

    # Success! Cure all afflictions
    if target_sid:
        target_session = online_sessions.get(target_sid, {})
        count = cure_all_afflictions(target_session)

        # Also wake from magical sleep
        if target_session.get("sleeping"):
            # Check if it's magical sleep vs rest sleep
            if has_affliction(target_session, "magic_sleep"):
                target_session["sleeping"] = False

        if count == 0 and not target_session.get("sleeping"):
            if target == player:
                return "You have no afflictions to cure."
            return f"{target.name} has no afflictions to cure."

        if target != player and count > 0:
            await utils.send_message(sio, target_sid, "You are now cured!")

        return f"You cure {count} affliction(s) from {target.name}!"
    else:
        return f"Cannot find {target.name}'s session."


async def handle_fod(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    sio: Any,
    utils: Any,
) -> str:
    """
    FOD (Finger of Death) - Instant death spell.

    Archmage only. Non-Archmages die (permadeath) if they attempt it.
    """
    from commands.combat import (
        handle_mob_defeat,
        end_combat,
        active_combats,
    )

    _spell_def = SPELL_DEFINITIONS["fod"]
    caster_sid = find_player_sid(player, online_sessions)

    # Check if caster is Archmage
    if player.level != "Archmage":
        # Non-Archmage attempts FOD = permadeath
        # Drop all items
        current_room = game_state.get_room(player.current_room)
        old_room = player.current_room

        for item in list(player.inventory):
            player.remove_item(item)
            current_room.add_item(item)

        # End any combat
        if player.name in active_combats:
            combat_data = active_combats[player.name]
            target_name = combat_data.get("target", "")
            end_combat(player.name, target_name)

        # Notify room
        from services.notifications import broadcast_room

        await broadcast_room(
            old_room,
            f"{player.name} utters forbidden words and is struck down by their own power!",
            exclude_player=[player.name],
        )

        # Set up permadeath (combat_death = True triggers persona reset)
        if caster_sid and caster_sid in online_sessions:
            online_sessions[caster_sid]["awaiting_respawn"] = True
            online_sessions[caster_sid]["combat_death"] = True

        # Put player in limbo
        player.current_room = None

        death_msg = "You attempt the forbidden spell...\n"
        death_msg += "Dark energy erupts from your fingertip and consumes you!\n"
        death_msg += "All your items have been dropped.\n\n"
        death_msg += "Persona reset.\nWould you like to play again?"

        if caster_sid:
            await utils.send_message(sio, caster_sid, death_msg)

        return ""  # Message already sent

    # Archmage casting FOD
    target_name = cmd.get("subject")
    if not target_name:
        return "Kill whom with the Finger of Death?"

    # Find target (player or mob)
    target, target_sid, is_mob = find_target_player_or_mob(
        target_name, player, game_state, online_sessions, utils
    )

    if not target:
        return f"There is no one called '{target_name}' here."

    if target == player:
        return "You cannot use the Finger of Death on yourself!"

    # FOD always succeeds for Archmages, no resistance

    # Broadcast the thunder of the Finger of Death to all players
    await broadcast_all(
        "You hear the crackling thunder of the Finger of Death!",
        exclude_players=[player.name, target.name],
    )

    if is_mob:
        # Kill mob instantly
        target.take_damage(target.max_stamina + 1)
        mob_manager = getattr(utils, "mob_manager", None)

        # Award points and handle loot
        await handle_mob_defeat(
            player,
            target,
            caster_sid,
            game_state,
            player_manager,
            online_sessions,
            mob_manager,
            sio,
            utils,
        )

        from services.notifications import broadcast_room

        await broadcast_room(
            player.current_room,
            f"{player.name} points their finger at {target.name}... and it crumbles to dust!",
            exclude_player=[player.name],
        )

        return f"You point your finger at {target.name}... and it crumbles to dust!"
    else:
        # Kill player - this is permadeath (combat_death = True)
        # Drop all target's items
        target_room = game_state.get_room(target.current_room)
        old_room = target.current_room

        for item in list(target.inventory):
            target.remove_item(item)
            target_room.add_item(item)
            # Broadcast item drop to other players
            await broadcast_item_drop(old_room, target.name, item.name)

        # End any combat the target is in
        if target.name in active_combats:
            combat_data = active_combats[target.name]
            combat_target_name = combat_data.get("target", "")
            end_combat(target.name, combat_target_name)

        # Notify room
        from services.notifications import broadcast_room

        await broadcast_room(
            old_room,
            f"{player.name} points their finger at {target.name}... and they fall dead!",
            exclude_player=[target.name, player.name],
        )

        # Set up permadeath for target
        if target_sid and target_sid in online_sessions:
            online_sessions[target_sid]["awaiting_respawn"] = True
            online_sessions[target_sid]["combat_death"] = True
            await utils.send_message(
                sio,
                target_sid,
                f"{player.name} points their finger at you...\n"
                f"A black bolt of energy lances through your body!\n"
                f"All your items have been dropped.\n\n"
                f"Persona reset.\nWould you like to play again?",
            )

        # Put target in limbo
        target.current_room = None
        player_manager.save_players()

        return f"You point your finger at {target.name}... and they fall dead!"


async def handle_spells(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    sio: Any,
    utils: Any,
) -> str:
    """
    SPELLS command - List all available spells with player's success chance.

    Matches MUD1 output format with explanatory text.
    """
    lines = []

    # Explanatory header
    lines.append(
        "Spells may be typed on their own, or with a target. Unless you are an "
        "Archmage, your chance of success varies with your magic ability. Targets "
        "with high magic may resist your spells. If a spell fails, it may backfire "
        "and affect you instead!"
    )
    lines.append("")
    lines.append(
        "The chance of success for each available spell at your level is shown below."
    )
    lines.append("")

    player_level_idx = get_level_index(player.level)
    is_archmage = player.level == "Archmage"

    # Spell descriptions for output (more detailed than help_text)
    spell_descriptions: Dict[str, Tuple[str, str]] = {
        "summon": (
            "SUMMON <player>",
            "Teleports the target to you, dropping all their items.",
        ),
        "force": (
            "FORCE <player> <command>",
            "Makes the target execute a command against their will.",
        ),
        "where": (
            "WHERE <item/player>",
            "Divines the location of an item or player.",
        ),
        "change": (
            "CHANGE <player>",
            "Changes the target's sex.",
        ),
        "sleep": (
            "SLEEP <player>",
            "Puts the target into a magical slumber.",
        ),
        "wish": (
            "WISH <message>",
            "Sends a message to the Archmages. Always succeeds.",
        ),
        "deafen": (
            "DEAFEN <player>",
            "Makes the target unable to hear any messages.",
        ),
        "blind": (
            "BLIND <player>",
            "Makes the target unable to see room descriptions.",
        ),
        "dumb": (
            "DUMB <player>",
            "Makes the target unable to speak.",
        ),
        "cripple": (
            "CRIPPLE <player>",
            "Makes the target unable to move.",
        ),
        "cure": (
            "CURE [player]",
            "Removes all afflictions. Targets yourself if no player given.",
        ),
        "fod": (
            "FOD <player>",
            "The Finger of Death. Instant kill, no resistance.",
        ),
    }

    for spell_name, spell_def in SPELL_DEFINITIONS.items():
        # Hide FOD from non-Archmages
        if spell_name == "fod" and not is_archmage:
            continue

        min_level = spell_def["min_level"]
        base_chance = spell_def["base_chance"]

        # Check if player can cast this spell
        can_cast = player_level_idx >= min_level

        # Calculate player's success chance
        if is_archmage:
            success_chance = 100
        else:
            success_chance = calculate_success_chance(player.magic, base_chance)

        # Get spell syntax and description
        syntax, description = spell_descriptions.get(
            spell_name, (spell_name.upper(), spell_def["help_text"])
        )

        # Format: SPELL <syntax>                   XX%
        if can_cast:
            lines.append(f"{syntax:35} {success_chance:3}%")
            lines.append(f"  {description}")
        else:
            min_level_name = LEVEL_NAMES[min_level]
            lines.append(f"{syntax:35} (requires {min_level_name})")
            lines.append(f"  {description}")

        lines.append("")

    return "\n".join(lines).rstrip()


# ===== COMMAND REGISTRATION =====


def register_spell_commands() -> None:
    """Register all spell commands with the command registry."""
    # Spell commands
    command_registry.register(
        "summon", handle_summon, "Summon a player to your location."
    )
    command_registry.register(
        "force", handle_force, "Force a player to execute a command."
    )
    command_registry.register("where", handle_where, "Locate an item or player.")
    command_registry.register("change", handle_change, "Change target's sex.")
    command_registry.register("wish", handle_wish, "Send a message to Archmages.")
    command_registry.register("deafen", handle_deafen, "Make target unable to hear.")
    command_registry.register("blind", handle_blind, "Make target unable to see.")
    command_registry.register("dumb", handle_dumb, "Make target unable to speak.")
    command_registry.register("cripple", handle_cripple, "Make target unable to move.")
    command_registry.register(
        "cure", handle_cure, "Remove all afflictions from target."
    )
    command_registry.register(
        "fod", handle_fod, "Finger of Death - Archmage only instant kill."
    )

    # Spells list command
    command_registry.register("spells", handle_spells, "List all available spells.")

    # Add spell verbs to vocabulary
    spell_verbs = [
        "summon",
        "force",
        "where",
        "change",
        "wish",
        "deafen",
        "blind",
        "dumb",
        "cripple",
        "cure",
        "fod",
        "spells",
    ]
    for verb in spell_verbs:
        vocabulary_manager.add_verb(verb)


# Register commands when module is imported
register_spell_commands()
