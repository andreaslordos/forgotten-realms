# backend/managers/mob_definitions.py

from models.Item import Item
from models.Weapon import Weapon


def get_mob_definitions():
    """
    Define mob templates that can be spawned in the game world.

    Returns:
        dict: Dictionary of mob_definition_id -> mob template
    """

    # Define loot items
    rusty_dagger = Weapon(
        name="rusty dagger",
        id="rusty_dagger",
        description="A worn dagger with a rusted blade. Better than nothing.",
        weight=0.5,
        value=5,
        takeable=True,
        damage=3,
        min_level="Neophyte",
        min_strength=0,
        min_dexterity=5,
    )

    gold_coin = Item(
        name="gold coin",
        id="gold_coin",
        description="A shiny gold coin.",
        weight=0.01,
        value=10,
        takeable=True,
    )

    tattered_cloak = Item(
        name="tattered cloak",
        id="tattered_cloak",
        description="A worn, tattered cloak that has seen better days.",
        weight=0.3,
        value=3,
        takeable=True,
    )

    wolf_pelt = Item(
        name="wolf pelt",
        id="wolf_pelt",
        description="A thick wolf pelt, still warm.",
        weight=2,
        value=15,
        takeable=True,
    )

    ancient_key = Item(
        name="ancient key",
        id="ancient_key",
        description="An ornate key covered in mysterious runes.",
        weight=0.1,
        value=0,
        takeable=True,
    )

    return {
        # Peaceful merchant - demonstrates non-aggressive mob
        "village_merchant": {
            "name": "village merchant",
            "description": "A portly merchant with a friendly smile stands here, eager to trade.",
            "strength": 15,
            "dexterity": 10,
            "max_stamina": 50,
            "damage": 2,
            "aggressive": False,
            "aggro_delay_min": 0,
            "aggro_delay_max": 0,
            "patrol_rooms": [],  # Stationary
            "movement_interval": 0,
            "loot_table": [
                {"item": gold_coin, "chance": 0.8},
                {"item": gold_coin, "chance": 0.5},  # Can drop multiple coins
            ],
            "instant_death": False,
            "point_value": 20,
            "pronouns": "he",
        },
        # Goblin scout - demonstrates delayed aggression and patrolling
        "goblin_scout": {
            "name": "goblin scout",
            "description": "A small, wiry goblin with darting eyes scouts the area nervously.",
            "strength": 25,
            "dexterity": 30,
            "max_stamina": 60,
            "damage": 7,
            "aggressive": True,
            "aggro_delay_min": 3,  # Becomes aggressive after 3-8 ticks
            "aggro_delay_max": 8,
            "patrol_rooms": [
                "forest_clearing",
                "forest_edge",
                "northern_path",
                "forest_hideaway",
            ],
            "movement_interval": 80,  # Moves every 8 ticks
            "loot_table": [
                {"item": rusty_dagger, "chance": 0.3},
                {"item": gold_coin, "chance": 0.6},
                {"item": tattered_cloak, "chance": 0.2},
            ],
            "instant_death": False,
            "point_value": 50,
            "pronouns": "it",
        },
        # Dire wolf - demonstrates instant aggressive (no delay) and valuable loot
        "dire_wolf": {
            "name": "dire wolf",
            "description": "A massive wolf with glowing red eyes and bared fangs snarls at you.",
            "strength": 35,
            "dexterity": 40,
            "max_stamina": 80,
            "damage": 12,
            "aggressive": True,
            "aggro_delay_min": 0,  # Instantly aggressive
            "aggro_delay_max": 0,
            "patrol_rooms": [],
            "movement_interval": 0,  # No movement
            "loot_table": [
                {"item": wolf_pelt, "chance": 0.9},
                {"item": gold_coin, "chance": 0.4},
            ],
            "instant_death": False,
            "point_value": 100,
            "pronouns": "it",
        },
        # Fragile skeleton - demonstrates instant death mechanic
        "brittle_skeleton": {
            "name": "brittle skeleton",
            "description": "An ancient skeleton held together by dark magic rattles ominously.",
            "strength": 20,
            "dexterity": 15,
            "max_stamina": 1,  # Will be ignored due to instant_death
            "damage": 5,
            "aggressive": True,
            "aggro_delay_min": 1,
            "aggro_delay_max": 3,
            "patrol_rooms": [],  # Stationary
            "movement_interval": 10,
            "loot_table": [
                {"item": ancient_key, "chance": 0.15},  # Rare drop
                {"item": rusty_dagger, "chance": 0.5},
            ],
            "instant_death": True,  # Dies in one hit
            "point_value": 30,
            "pronouns": "it",
        },
        # Wandering elder - peaceful mob that patrols (for quests/interactions)
        "elder_sage": {
            "name": "Elder",
            "description": "The village Elder wanders slowly, lost in thought about the nature of time...",
            "strength": 10,
            "dexterity": 10,
            "max_stamina": 40,
            "damage": 1,
            "aggressive": False,
            "aggro_delay_min": 0,
            "aggro_delay_max": 0,
            "patrol_rooms": ["cottage_garden", "elders_cottage", "cottage_interior"],
            "movement_interval": 240,  # Slow movement
            "loot_table": [
                {"item": ancient_key, "chance": 1.0}  # Always drops key (for quest)
            ],
            "instant_death": False,
            "point_value": 0,  # No points for killing peaceful NPCs
            "pronouns": "she",
        },
        # Guard captain - strong mob with high stats
        "guard_captain": {
            "name": "guard captain",
            "description": "A stern-faced captain of the guard watches the area vigilantly.",
            "strength": 45,
            "dexterity": 35,
            "max_stamina": 120,
            "damage": 15,
            "aggressive": False,  # Only attacks if provoked
            "aggro_delay_min": 0,
            "aggro_delay_max": 0,
            "patrol_rooms": ["spawn", "marketplace", "tower_interior"],
            "movement_interval": 120,
            "loot_table": [
                {"item": gold_coin, "chance": 1.0},
                {"item": gold_coin, "chance": 0.8},
                {"item": gold_coin, "chance": 0.6},
            ],
            "instant_death": False,
            "point_value": 150,
            "pronouns": "he",
        },
    }
