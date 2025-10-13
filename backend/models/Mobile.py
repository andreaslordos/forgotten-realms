# backend/models/Mobile.py

from models.StatefulItem import StatefulItem
from models.Item import Item
import random
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Mobile(StatefulItem):
    """
    Mobile (Mob) - An NPC that can move, fight, and interact with players.
    Inherits from StatefulItem to enable special interactions (e.g., give/show commands).
    """

    def __init__(
        self,
        name,
        id,
        description,
        strength=20,
        dexterity=20,
        max_stamina=100,
        damage=5,
        aggressive=False,
        aggro_delay_min=0,
        aggro_delay_max=0,
        patrol_rooms=None,
        movement_interval=10,
        loot_table=None,
        instant_death=False,
        point_value=0,
        pronouns="it",
        current_room=None,
    ):
        """
        Initialize a Mobile.

        Args:
            name (str): The mob's name
            id (str): Unique identifier
            description (str): Description shown when looking at the mob
            strength (int): Determines damage dealt
            dexterity (int): Determines hit chance
            max_stamina (int): Maximum health
            damage (int): Base damage dealt in combat
            aggressive (bool): Whether mob attacks players on sight
            aggro_delay_min (int): Minimum ticks before turning aggressive (if aggressive=True)
            aggro_delay_max (int): Maximum ticks before turning aggressive (if aggressive=True)
            patrol_rooms (list): List of room IDs the mob patrols (None = stationary)
            movement_interval (int): Ticks between movements
            loot_table (list): List of {"item": item_obj, "chance": float} for drops
            instant_death (bool): If True, mob dies in one hit
            point_value (int): Points awarded to player on death
            pronouns (str): "he", "she", "it", "they" for descriptions
            current_room (str): Current room ID
        """
        # Initialize as StatefulItem (for interactions), not takeable
        super().__init__(
            name=name,
            id=id,
            description=description,
            weight=9999,
            value=0,
            takeable=False,
            state="alive",
        )

        # Combat stats
        self.strength = strength
        self.dexterity = dexterity
        self.max_stamina = max_stamina
        self.stamina = max_stamina
        self.damage = damage
        self.instant_death = instant_death
        self.point_value = point_value

        # Behavior
        self.aggressive = aggressive
        self.aggro_delay_min = aggro_delay_min
        self.aggro_delay_max = aggro_delay_max
        self.aggro_tick_counter = None  # Set when mob spawns
        self.target_player = None  # Current combat target (Player object)

        # Movement
        self.patrol_rooms = patrol_rooms if patrol_rooms else []
        self.movement_interval = movement_interval
        self.last_move_tick = 0
        self.current_patrol_index = 0

        # Loot
        self.loot_table = loot_table if loot_table else []

        # Location and identity
        self.current_room = current_room
        self.pronouns = pronouns

        # Add state descriptions for alive/dead
        self.add_state_description("alive", description)
        self.add_state_description("dead", f"The corpse of {name} lies here.")

        logger.info(f"Created mob: {name} (ID: {id}) in room {current_room}")

    def initialize_aggro_delay(self):
        """
        Set the initial aggro delay based on the configured range.
        Called when the mob is spawned.
        """
        if self.aggressive and self.aggro_delay_max > 0:
            self.aggro_tick_counter = random.randint(
                self.aggro_delay_min, self.aggro_delay_max
            )
            logger.debug(
                f"{self.name} will become aggressive in {self.aggro_tick_counter} ticks"
            )
        else:
            self.aggro_tick_counter = 0

    def can_attack_player(self):
        """
        Check if the mob should initiate combat with a player.

        Returns:
            bool: True if mob can attack
        """
        if self.state != "alive":
            return False

        if not self.aggressive:
            return False

        # If there's an aggro delay, check if it's elapsed
        if self.aggro_tick_counter is not None and self.aggro_tick_counter > 0:
            return False

        # Already in combat
        if self.target_player is not None:
            return False

        return True

    def tick_aggro_counter(self):
        """Decrement the aggro counter each tick."""
        if self.aggro_tick_counter is not None and self.aggro_tick_counter > 0:
            self.aggro_tick_counter -= 1
            if self.aggro_tick_counter == 0:
                logger.info(f"{self.name} is now aggressive!")

    def should_move(self, current_tick):
        """
        Check if the mob should move this tick.

        Args:
            current_tick (int): Current game tick

        Returns:
            bool: True if mob should move
        """
        if self.state != "alive":
            return False

        if not self.patrol_rooms or len(self.patrol_rooms) < 2:
            return False

        # Don't move if in combat
        if self.target_player is not None:
            return False

        # Check if enough ticks have passed
        if current_tick - self.last_move_tick >= self.movement_interval:
            return True

        return False

    def choose_next_room(self):
        """
        Choose the next room to patrol to.

        Returns:
            str: Room ID to move to
        """
        if not self.patrol_rooms or len(self.patrol_rooms) < 2:
            return self.current_room

        # Move to next room in patrol list (circular)
        self.current_patrol_index = (self.current_patrol_index + 1) % len(
            self.patrol_rooms
        )
        return self.patrol_rooms[self.current_patrol_index]

    def move_to_room(self, room_id, current_tick):
        """
        Move the mob to a new room.

        Args:
            room_id (str): Room to move to
            current_tick (int): Current game tick
        """
        old_room = self.current_room
        self.current_room = room_id
        self.last_move_tick = current_tick
        logger.info(f"{self.name} moved from {old_room} to {room_id}")

    def take_damage(self, amount):
        """
        Apply damage to the mob.

        Args:
            amount (int): Damage to apply

        Returns:
            tuple: (is_dead, remaining_stamina)
        """
        if self.instant_death:
            self.stamina = 0
            self.state = "dead"
            logger.info(f"{self.name} died instantly!")
            return True, 0

        self.stamina = max(0, self.stamina - amount)

        if self.stamina <= 0:
            self.state = "dead"
            self.description = self.state_descriptions.get(
                "dead", f"The corpse of {self.name}."
            )
            logger.info(f"{self.name} has been slain!")
            return True, 0

        return False, self.stamina

    def drop_loot(self):
        """
        Roll the loot table and return items to drop.

        Returns:
            list: List of Item objects to drop
        """
        dropped_items = []

        for loot_entry in self.loot_table:
            item_obj = loot_entry.get("item")
            chance = loot_entry.get("chance", 0.0)

            # Roll for drop
            if random.random() <= chance:
                # Create a copy of the item to drop
                dropped_items.append(item_obj)
                logger.info(f"{self.name} dropped {item_obj.name}")

        return dropped_items

    def is_mob(self):
        """Helper method to identify this as a mob."""
        return True

    def to_dict(self):
        """Convert the mobile to a dictionary for serialization."""
        data = super().to_dict()
        data.update(
            {
                "mob_type": "mobile",
                "strength": self.strength,
                "dexterity": self.dexterity,
                "max_stamina": self.max_stamina,
                "stamina": self.stamina,
                "damage": self.damage,
                "instant_death": self.instant_death,
                "point_value": self.point_value,
                "aggressive": self.aggressive,
                "aggro_delay_min": self.aggro_delay_min,
                "aggro_delay_max": self.aggro_delay_max,
                "aggro_tick_counter": self.aggro_tick_counter,
                "patrol_rooms": self.patrol_rooms,
                "movement_interval": self.movement_interval,
                "last_move_tick": self.last_move_tick,
                "current_patrol_index": self.current_patrol_index,
                "loot_table": [
                    {"item": item.to_dict(), "chance": entry["chance"]}
                    for entry in self.loot_table
                    for item in [entry["item"]]
                ],
                "current_room": self.current_room,
                "pronouns": self.pronouns,
            }
        )
        return data

    @staticmethod
    def from_dict(data):
        """Create a mobile from a dictionary representation."""
        # Reconstruct loot table with Item objects
        loot_table = []
        for entry in data.get("loot_table", []):
            item_data = entry["item"]
            # Reconstruct item based on type
            if item_data.get("item_type") == "weapon":
                from models.Weapon import Weapon

                item_obj = Weapon.from_dict(item_data)
            else:
                item_obj = Item.from_dict(item_data)
            loot_table.append({"item": item_obj, "chance": entry["chance"]})

        mob = Mobile(
            name=data["name"],
            id=data["id"],
            description=data["description"],
            strength=data.get("strength", 20),
            dexterity=data.get("dexterity", 20),
            max_stamina=data.get("max_stamina", 100),
            damage=data.get("damage", 5),
            aggressive=data.get("aggressive", False),
            aggro_delay_min=data.get("aggro_delay_min", 0),
            aggro_delay_max=data.get("aggro_delay_max", 0),
            patrol_rooms=data.get("patrol_rooms", []),
            movement_interval=data.get("movement_interval", 10),
            loot_table=loot_table,
            instant_death=data.get("instant_death", False),
            point_value=data.get("point_value", 0),
            pronouns=data.get("pronouns", "it"),
            current_room=data.get("current_room"),
        )

        # Restore state
        mob.stamina = data.get("stamina", mob.max_stamina)
        mob.state = data.get("state", "alive")
        mob.aggro_tick_counter = data.get("aggro_tick_counter")
        mob.last_move_tick = data.get("last_move_tick", 0)
        mob.current_patrol_index = data.get("current_patrol_index", 0)

        # Restore state descriptions if present
        if "state_descriptions" in data:
            mob.state_descriptions = data["state_descriptions"]

        return mob

    def __repr__(self):
        return f"Mobile({self.name}, room={self.current_room}, state={self.state}, stamina={self.stamina}/{self.max_stamina})"
