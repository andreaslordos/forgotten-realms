# backend/models/Weapon.py

from models.Item import Item


class Weapon(Item):
    """
    A weapon that can be used in combat.
    Extends the base Item class with combat-specific attributes.
    """

    def __init__(
        self,
        name,
        id,
        description,
        weight=1,
        value=0,
        takeable=True,
        damage=5,
        min_level=0,
        min_strength=0,
        min_dexterity=0,
    ):
        """
        Initialize a Weapon.

        Args:
            name (str): The name of the weapon
            id (str): The unique identifier
            description (str): A description of the weapon
            weight (float): The weight of the weapon in kg
            value (int): The value in points if swamped
            takeable (bool): Whether the weapon can be picked up
            damage (int): The base damage of the weapon
            min_level (str): The minimum level required to use the weapon
            min_strength (int): The minimum strength required to use the weapon
            min_dexterity (int): The minimum dexterity required to use the weapon
        """
        super().__init__(name, id, description, weight, value, takeable)
        self.damage = damage
        self.min_level = min_level
        self.min_strength = min_strength
        self.min_dexterity = min_dexterity
        self.weapon_type = "melee"  # Default weapon type

    def can_use(self, player):
        """
        Check if a player meets the requirements to use this weapon.

        Args:
            player (Player): The player to check

        Returns:
            tuple: (bool, str) indicating if the player can use the weapon and why not
        """
        # Check level requirement
        if self.min_level and player.level != self.min_level:
            level_names = {
                "Neophyte": 0,
                "Novice": 1,
                "Acolyte": 2,
                "Scholar": 3,
                "Magister": 4,
                "Archon": 5,
                "Warlock": 6,
                "Guardian": 7,
                "Sovereign": 8,
                "Archmage": 9,
            }

            # Get the numeric level of the player and required level
            player_level_num = level_names.get(player.level, -1)
            required_level_num = level_names.get(self.min_level, -1)

            if player_level_num < required_level_num:
                return (
                    False,
                    f"You must be at least a {self.min_level} to use {self.name}.",
                )

        # Check strength requirement
        if self.min_strength > 0 and player.strength < self.min_strength:
            return False, f"You need {self.min_strength} strength to wield {self.name}."

        # Check dexterity requirement
        if self.min_dexterity > 0 and player.dexterity < self.min_dexterity:
            return False, f"You need {self.min_dexterity} dexterity to use {self.name}."

        return True, ""

    def to_dict(self):
        """Convert the weapon to a dictionary for serialization."""
        data = super().to_dict()
        data["damage"] = self.damage
        data["min_level"] = self.min_level
        data["min_strength"] = self.min_strength
        data["min_dexterity"] = self.min_dexterity
        data["weapon_type"] = self.weapon_type
        data["item_type"] = "weapon"  # Add type marker
        return data

    @staticmethod
    def from_dict(data):
        """Create a weapon from a dictionary representation."""
        weapon = Weapon(
            name=data["name"],
            id=data["id"],
            description=data["description"],
            weight=data.get("weight", 1),
            value=data.get("value", 0),
            takeable=data.get("takeable", True),
            damage=data.get("damage", 5),
            min_level=data.get("min_level", 0),
            min_strength=data.get("min_strength", 0),
            min_dexterity=data.get("min_dexterity", 0),
        )
        if "weapon_type" in data:
            weapon.weapon_type = data["weapon_type"]
        return weapon
