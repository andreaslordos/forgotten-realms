# backend/managers/world/shared_items.py
"""
Shared item templates and factory functions for creating common items.

These items are used across multiple levels in the game world.
"""

from models.Item import Item
from models.Weapon import Weapon
from models.StatefulItem import StatefulItem


# ============================================================================
# BASIC ITEMS
# ============================================================================


def create_torch() -> Item:
    """Create a torch that emits light."""
    return Item(
        name="torch",
        id="torch",
        description="A wooden torch wrapped in oil-soaked cloth. It burns steadily.",
        weight=1,
        value=5,
        takeable=True,
        emits_light=True,
    )


def create_lantern() -> Item:
    """Create a lantern that emits light."""
    return Item(
        name="lantern",
        id="lantern",
        description="A brass lantern with a flickering flame inside.",
        weight=2,
        value=15,
        takeable=True,
        emits_light=True,
    )


def create_coin(coin_id: str = "coin") -> Item:
    """Create a gold coin."""
    return Item(
        name="coin",
        id=coin_id,
        description="A tarnished gold coin bearing an unfamiliar face.",
        weight=0,
        value=10,
        takeable=True,
    )


def create_key(key_id: str, description: str) -> Item:
    """Create a key with custom ID and description."""
    return Item(
        name="key",
        id=key_id,
        description=description,
        weight=0,
        value=5,
        takeable=True,
    )


def create_bone() -> Item:
    """Create a bone item."""
    return Item(
        name="bone",
        id="bone",
        description="A yellowed bone, origin unknown.",
        weight=1,
        value=2,
        takeable=True,
    )


def create_holy_bones() -> Item:
    """Create the holy bones of St. Andral."""
    return Item(
        name="bones",
        id="bones",
        description="The sacred bones of St. Andral, wrapped in a velvet cloth. They radiate warmth.",
        weight=2,
        value=100,
        takeable=True,
    )


def create_wine() -> Item:
    """Create a bottle of wine."""
    return Item(
        name="wine",
        id="wine",
        description="A dusty bottle of purple wine from the Wizard of Wines winery.",
        weight=1,
        value=8,
        takeable=True,
    )


# ============================================================================
# LEVEL TRANSITION ITEMS
# ============================================================================


def create_mist_token() -> Item:
    """Create the mist token that allows passage through the mist barrier."""
    return Item(
        name="mist token",
        id="mist_token",
        description=(
            "A small silver token inscribed with ancient runes. "
            "It pulses with a faint, otherworldly light. "
            "The mists seem to recoil from it."
        ),
        weight=0,
        value=50,
        takeable=True,
    )


def create_knight_medallion() -> Item:
    """Create the knight's medallion for the bridge guardian."""
    return Item(
        name="medallion",
        id="knight_medallion",
        description=(
            "A silver medallion bearing the crest of a knight's order - "
            "a dragon coiled around a sword. It feels cold to the touch."
        ),
        weight=0,
        value=40,
        takeable=True,
    )


def create_shadow_key() -> Item:
    """Create the shadow key from the hag's domain."""
    return Item(
        name="shadow key",
        id="shadow_key",
        description=(
            "A key made of solidified shadow. It seems to absorb light "
            "and feels ice cold. Dark whispers echo from it."
        ),
        weight=0,
        value=75,
        takeable=True,
    )


# ============================================================================
# WEAPONS
# ============================================================================


def create_rusty_dagger() -> Weapon:
    """Create a basic rusty dagger."""
    return Weapon(
        name="rusty dagger",
        id="rusty_dagger",
        description="A corroded dagger with a chipped blade. Better than nothing.",
        weight=1,
        value=5,
        takeable=True,
        damage=3,
        min_level="Neophyte",
        min_strength=0,
        min_dexterity=0,
    )


def create_wooden_club() -> Weapon:
    """Create a basic wooden club."""
    return Weapon(
        name="wooden club",
        id="wooden_club",
        description="A heavy wooden club, rough-hewn but effective.",
        weight=3,
        value=3,
        takeable=True,
        damage=4,
        min_level="Neophyte",
        min_strength=5,
        min_dexterity=0,
    )


def create_short_sword() -> Weapon:
    """Create a short sword."""
    return Weapon(
        name="short sword",
        id="short_sword",
        description="A well-balanced short sword with a leather-wrapped hilt.",
        weight=2,
        value=20,
        takeable=True,
        damage=6,
        min_level="Apprentice",
        min_strength=10,
        min_dexterity=5,
    )


def create_silver_dagger() -> Weapon:
    """Create a silver dagger effective against undead."""
    return Weapon(
        name="silver dagger",
        id="silver_dagger",
        description="A dagger of pure silver, deadly to creatures of the night.",
        weight=1,
        value=50,
        takeable=True,
        damage=8,
        min_level="Neophyte",
        min_strength=0,
        min_dexterity=5,
    )


# ============================================================================
# STATEFUL ITEM HELPERS
# ============================================================================


def create_locked_door(
    door_id: str,
    name: str,
    description_locked: str,
    description_unlocked: str,
    key_id: str,
    exit_direction: str,
    exit_room: str,
    room_id: str,
) -> StatefulItem:
    """
    Create a locked door that requires a key to open.

    Args:
        door_id: Unique ID for the door.
        name: Display name of the door.
        description_locked: Description when door is locked.
        description_unlocked: Description when door is unlocked.
        key_id: ID of the key item required.
        exit_direction: Direction the door leads (e.g., "north").
        exit_room: Room ID the door leads to.
        room_id: Room ID where this door is placed.

    Returns:
        A configured StatefulItem representing the door.
    """
    door = StatefulItem(
        name=name,
        id=door_id,
        description=description_locked,
        state="locked",
        takeable=False,
        room_id=room_id,
    )
    door.add_state_description("locked", description_locked)
    door.add_state_description("unlocked", description_unlocked)

    door.add_interaction(
        verb="unlock",
        required_instrument=key_id,
        from_state="locked",
        target_state="unlocked",
        message="You insert the key. The lock clicks open!",
        add_exit=(exit_direction, exit_room),
    )

    door.add_interaction(
        verb="open",
        from_state="locked",
        message="The door is locked. You need a key.",
    )

    door.add_interaction(
        verb="open",
        from_state="unlocked",
        message="The door is already open.",
    )

    return door
