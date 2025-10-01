# backend/managers/mob_manager.py

import json
import os
import logging
from models.Mobile import Mobile
from models.Item import Item

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MobManager:
    """
    Manages all mobs in the game world.
    Handles spawning, tracking, AI ticking, and persistence.
    """

    def __init__(self, save_file="storage/mobs.json"):
        self.save_file = save_file
        self.mobs = {}  # Dict of mob_id -> Mobile instance
        self.mob_definitions = {}  # Dict of definition_id -> mob template
        self.global_tick_counter = 0  # Track ticks for movement timing
        self.load_mobs()

    def load_mob_definitions(self, definitions):
        """
        Load mob definition templates.

        Args:
            definitions (dict): Dict of definition_id -> template dict
        """
        self.mob_definitions = definitions
        logger.info(f"Loaded {len(definitions)} mob definitions")

    def spawn_mob(self, definition_id, room_id, game_state=None):
        """
        Spawn a mob from a definition template.

        Args:
            definition_id (str): ID of the mob definition
            room_id (str): Room to spawn the mob in
            game_state (GameState, optional): Game state for room access

        Returns:
            Mobile: The spawned mob instance, or None if definition not found
        """
        if definition_id not in self.mob_definitions:
            logger.error(f"Mob definition '{definition_id}' not found!")
            return None

        template = self.mob_definitions[definition_id]

        # Generate unique mob ID
        mob_id = f"{definition_id}_{len(self.mobs)}_{room_id}"

        # Reconstruct loot table with Item objects
        loot_table = []
        for loot_entry in template.get("loot_table", []):
            # loot_entry should be {"item": Item object, "chance": float}
            loot_table.append(loot_entry)

        # Create the mob
        mob = Mobile(
            name=template["name"],
            id=mob_id,
            description=template.get("description", f"A {template['name']} stands here."),
            strength=template.get("strength", 20),
            dexterity=template.get("dexterity", 20),
            max_stamina=template.get("max_stamina", 100),
            damage=template.get("damage", 5),
            aggressive=template.get("aggressive", False),
            aggro_delay_min=template.get("aggro_delay_min", 0),
            aggro_delay_max=template.get("aggro_delay_max", 0),
            patrol_rooms=template.get("patrol_rooms", []),
            movement_interval=template.get("movement_interval", 10),
            loot_table=loot_table,
            instant_death=template.get("instant_death", False),
            point_value=template.get("point_value", 0),
            pronouns=template.get("pronouns", "it"),
            current_room=room_id
        )

        # Initialize aggro delay
        mob.initialize_aggro_delay()

        # Add to tracking
        self.mobs[mob_id] = mob

        # Add mob to room if game_state provided
        if game_state:
            room = game_state.get_room(room_id)
            if room:
                room.add_item(mob)  # Mobs are added as items to rooms

        logger.info(f"Spawned {mob.name} (ID: {mob_id}) in room {room_id}")
        return mob

    def remove_mob(self, mob_id, game_state=None):
        """
        Remove a mob from the game.

        Args:
            mob_id (str): ID of the mob to remove
            game_state (GameState, optional): Game state for room cleanup

        Returns:
            bool: True if removed, False if not found
        """
        if mob_id not in self.mobs:
            return False

        mob = self.mobs[mob_id]

        # Remove from room if game_state provided
        if game_state and mob.current_room:
            room = game_state.get_room(mob.current_room)
            if room:
                room.remove_item(mob)

        # Remove from tracking
        del self.mobs[mob_id]
        logger.info(f"Removed mob {mob.name} (ID: {mob_id})")
        return True

    def get_mob(self, mob_id):
        """Get a mob by ID."""
        return self.mobs.get(mob_id)

    def get_mobs_in_room(self, room_id):
        """
        Get all mobs in a specific room.

        Args:
            room_id (str): Room ID to search

        Returns:
            list: List of Mobile objects in the room
        """
        return [mob for mob in self.mobs.values() if mob.current_room == room_id and mob.state == "alive"]

    def get_all_mobs(self):
        """Get all mobs (alive and dead)."""
        return list(self.mobs.values())

    async def tick_all_mobs(self, sio, online_sessions, player_manager, game_state, utils):
        """
        Process one tick for all mobs (AI, movement, aggro).

        Args:
            sio: Socket.IO instance
            online_sessions: Dict of active player sessions
            player_manager: PlayerManager instance
            game_state: GameState instance
            utils: Utils module
        """
        self.global_tick_counter += 1

        for mob_id, mob in list(self.mobs.items()):
            if mob.state != "alive":
                continue

            # Tick aggro counter
            mob.tick_aggro_counter()

            # Check if mob should move
            if mob.should_move(self.global_tick_counter):
                await self._process_mob_movement(mob, game_state, online_sessions, sio, utils)

            # Check if mob should initiate combat
            if mob.can_attack_player():
                await self._process_mob_aggression(mob, online_sessions, player_manager, game_state, sio, utils)

    async def _process_mob_movement(self, mob, game_state, online_sessions, sio, utils):
        """
        Handle mob movement along patrol route.

        Args:
            mob: Mobile instance
            game_state: GameState instance
            online_sessions: Dict of active sessions
            sio: Socket.IO instance
            utils: Utils module
        """
        old_room_id = mob.current_room
        new_room_id = mob.choose_next_room()

        if new_room_id == old_room_id:
            return

        # Remove from old room
        old_room = game_state.get_room(old_room_id)
        if old_room:
            old_room.remove_item(mob)

            # Notify players in old room
            if online_sessions and sio and utils:
                for sid, session_data in online_sessions.items():
                    player = session_data.get('player')
                    if player and player.current_room == old_room_id:
                        await utils.send_message(sio, sid, f"{mob.name.capitalize()} leaves.")

        # Move mob
        mob.move_to_room(new_room_id, self.global_tick_counter)

        # Add to new room
        new_room = game_state.get_room(new_room_id)
        if new_room:
            new_room.add_item(mob)

            # Notify players in new room
            if online_sessions and sio and utils:
                for sid, session_data in online_sessions.items():
                    player = session_data.get('player')
                    if player and player.current_room == new_room_id:
                        await utils.send_message(sio, sid, f"{mob.name.capitalize()} arrives.")

    async def _process_mob_aggression(self, mob, online_sessions, player_manager, game_state, sio, utils):
        """
        Handle aggressive mob initiating combat.

        Args:
            mob: Mobile instance
            online_sessions: Dict of active sessions
            player_manager: PlayerManager instance
            game_state: GameState instance
            sio: Socket.IO instance
            utils: Utils module
        """
        # Find a player in the same room to attack
        target_player = None
        target_sid = None

        if online_sessions:
            for sid, session_data in online_sessions.items():
                player = session_data.get('player')
                if player and player.current_room == mob.current_room:
                    target_player = player
                    target_sid = sid
                    break

        if not target_player:
            return

        # Import combat module to initiate attack
        from commands.combat import mob_initiate_attack
        await mob_initiate_attack(mob, target_player, target_sid, player_manager, game_state, online_sessions, sio, utils)

    def save_mobs(self):
        """Save all mobs to file."""
        # Ensure directory exists
        directory = os.path.dirname(self.save_file)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

        with open(self.save_file, "w") as f:
            mob_data = {mob_id: mob.to_dict() for mob_id, mob in self.mobs.items()}
            json.dump(mob_data, f, indent=4)

        logger.info(f"Saved {len(self.mobs)} mobs to {self.save_file}")

    def load_mobs(self):
        """Load mobs from file."""
        if os.path.exists(self.save_file):
            with open(self.save_file, "r") as f:
                data = json.load(f)
                self.mobs = {mob_id: Mobile.from_dict(mob_data) for mob_id, mob_data in data.items()}
                logger.info(f"Loaded {len(self.mobs)} mobs from {self.save_file}")
        else:
            self.mobs = {}
            logger.info("No saved mobs found, starting fresh")
