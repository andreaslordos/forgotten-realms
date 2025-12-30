# backend/managers/mob_manager.py

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from models.Mobile import Mobile
from services.invisibility_service import is_invisible

if TYPE_CHECKING:
    from managers.game_state import GameState
    from managers.player import PlayerManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MobManager:
    """
    Manages all mobs in the game world.
    Handles spawning, tracking, and AI ticking.
    """

    mobs: Dict[str, Mobile]
    mob_definitions: Dict[str, Dict[str, Any]]
    global_tick_counter: int

    def __init__(self) -> None:
        self.mobs = {}  # Dict of mob_id -> Mobile instance
        self.mob_definitions = {}  # Dict of definition_id -> mob template
        self.global_tick_counter = 0  # Track ticks for movement timing

    def load_mob_definitions(self, definitions: Dict[str, Dict[str, Any]]) -> None:
        """
        Load mob definition templates.

        Args:
            definitions (dict): Dict of definition_id -> template dict
        """
        self.mob_definitions = definitions
        logger.info(f"Loaded {len(definitions)} mob definitions")

    def spawn_mob(
        self, definition_id: str, room_id: str, game_state: Optional["GameState"] = None
    ) -> Optional[Mobile]:
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
        loot_table: List[Dict[str, Any]] = []
        for loot_entry in template.get("loot_table", []):
            # loot_entry should be {"item": Item object, "chance": float}
            loot_table.append(loot_entry)

        # Create the mob
        mob = Mobile(
            name=template["name"],
            id=mob_id,
            description=template.get(
                "description", f"A {template['name']} stands here."
            ),
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
            current_room=room_id,
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

    def remove_mob(self, mob_id: str, game_state: Optional["GameState"] = None) -> bool:
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

    def get_mob(self, mob_id: str) -> Optional[Mobile]:
        """Get a mob by ID."""
        return self.mobs.get(mob_id)

    def get_mobs_in_room(self, room_id: str) -> List[Mobile]:
        """
        Get all mobs in a specific room.

        Args:
            room_id (str): Room ID to search

        Returns:
            list: List of Mobile objects in the room
        """
        return [
            mob
            for mob in self.mobs.values()
            if mob.current_room == room_id and mob.state == "alive"
        ]

    def get_all_mobs(self) -> List[Mobile]:
        """Get all mobs (alive and dead)."""
        return list(self.mobs.values())

    async def tick_all_mobs(
        self,
        sio: Any,
        online_sessions: Dict[str, Dict[str, Any]],
        player_manager: "PlayerManager",
        game_state: "GameState",
        utils: Any,
    ) -> None:
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

        from commands.combat import is_in_combat

        for mob_id, mob in list(self.mobs.items()):
            if mob.state != "alive":
                continue

            if is_in_combat(mob_id):
                logger.debug(f"Skipping movement for {mob.name} while in combat")
                continue

            # Tick aggro counter
            mob.tick_aggro_counter()

            # Check if mob should move
            if mob.should_move(self.global_tick_counter):
                await self._process_mob_movement(
                    mob, game_state, online_sessions, sio, utils
                )

            # Check if mob should initiate combat
            if mob.can_attack_player():
                await self._process_mob_aggression(
                    mob, online_sessions, player_manager, game_state, sio, utils
                )

    async def _process_mob_movement(
        self,
        mob: Mobile,
        game_state: "GameState",
        online_sessions: Dict[str, Dict[str, Any]],
        sio: Any,
        utils: Any,
    ) -> None:
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
        old_room = game_state.get_room(old_room_id) if old_room_id else None
        if old_room:
            old_room.remove_item(mob)

            # Notify players in old room
            if online_sessions and sio and utils:
                for sid, session_data in online_sessions.items():
                    player = session_data.get("player")
                    if player and player.current_room == old_room_id:
                        await utils.send_message(
                            sio, sid, f"{mob.name.capitalize()} leaves."
                        )

        # Move mob
        if new_room_id is not None:
            mob.move_to_room(new_room_id, self.global_tick_counter)

        # Add to new room
        new_room = game_state.get_room(new_room_id) if new_room_id else None
        if new_room:
            new_room.add_item(mob)

            # Notify players in new room
            if online_sessions and sio and utils:
                players_in_room = False
                for sid, session_data in online_sessions.items():
                    player = session_data.get("player")
                    if player and player.current_room == new_room_id:
                        players_in_room = True
                        await utils.send_message(
                            sio, sid, f"{mob.name.capitalize()} arrives."
                        )

                # If mob is aggressive and moved into room with players,
                # reset aggro delay to give players time to react
                if players_in_room and mob.aggressive and mob.state == "alive":
                    mob.initialize_aggro_delay()

    async def _process_mob_aggression(
        self,
        mob: Mobile,
        online_sessions: Dict[str, Dict[str, Any]],
        player_manager: "PlayerManager",
        game_state: "GameState",
        sio: Any,
        utils: Any,
    ) -> None:
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
                player = session_data.get("player")
                # Players in limbo (current_room == None) won't match
                # Invisible players can't be detected by mobs
                if (
                    player
                    and player.current_room == mob.current_room
                    and not is_invisible(player, online_sessions)
                ):
                    target_player = player
                    target_sid = sid
                    break

        if not target_player or not target_sid:
            return

        # Import combat module to initiate attack
        from commands.combat import mob_initiate_attack

        await mob_initiate_attack(
            mob,
            target_player,
            target_sid,
            player_manager,
            game_state,
            online_sessions,
            sio,
            utils,
        )
