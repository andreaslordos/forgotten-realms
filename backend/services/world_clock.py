# backend/services/world_clock.py
"""
Day/night cycle for the Mournvale.

Night means DANGER, not blindness: night-only mobs emerge at dusk and
dissipate at dawn, and aggressive mobs strike harder in the dark. Room
visibility is untouched — hiding text in a text game punishes rather than
thrills. Lanterns keep their value in the world's permanently dark interiors.
"""

import logging
import time
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

DAY_SECONDS = 1800.0  # 30 minutes of daylight
NIGHT_SECONDS = 900.0  # 15 minutes of night
CYCLE_SECONDS = DAY_SECONDS + NIGHT_SECONDS

NIGHT_HIT_BONUS = 10  # Aggressive mobs strike truer in the dark

DUSK_MESSAGE = (
    "The last light drains out of the sky. Night falls across the Mournvale, "
    "and somewhere far off, a howl rises."
)
DAWN_MESSAGE = (
    "A grey dawn breaks over the Mournvale. Whatever walked the night "
    "slinks back into the shadows."
)

TimeFunc = Callable[[], float]


class WorldClock:
    """Deterministic day/night clock with dusk/dawn transition handling."""

    def __init__(
        self,
        time_func: Optional[TimeFunc] = None,
        epoch: Optional[float] = None,
    ) -> None:
        self._time: TimeFunc = time_func or time.time
        self.epoch: float = epoch if epoch is not None else self._time()
        self._last_phase: str = self.phase()
        # mob_ids of night mobs we spawned, to despawn at dawn
        self._night_mob_ids: List[str] = []

    def _cycle_position(self) -> float:
        return (self._time() - self.epoch) % CYCLE_SECONDS

    def is_night(self) -> bool:
        """True during the night portion of the cycle."""
        return self._cycle_position() >= DAY_SECONDS

    def phase(self) -> str:
        return "night" if self.is_night() else "day"

    def seconds_until_transition(self) -> float:
        """Seconds until the next dusk or dawn."""
        position = self._cycle_position()
        if position < DAY_SECONDS:
            return DAY_SECONDS - position
        return CYCLE_SECONDS - position

    def describe(self) -> str:
        """Player-facing time report for the 'time' command."""
        minutes = int(self.seconds_until_transition() // 60)
        if self.is_night():
            if minutes < 1:
                return "It is night. Dawn is moments away."
            return f"It is night. Dawn breaks in about {minutes} minute(s)."
        if minutes < 1:
            return "It is day, but the light is failing - dusk is moments away."
        return f"It is day. Dusk falls in about {minutes} minute(s)."

    async def tick(
        self,
        sio: Any,
        online_sessions: Dict[str, Dict[str, Any]],
        game_state: Any,
        utils: Any,
        mob_manager: Any,
    ) -> Optional[str]:
        """
        Detect phase transitions; broadcast atmosphere and manage night mobs.

        Returns the phase entered ("night"/"day") on a transition, else None.
        """
        current = self.phase()
        if current == self._last_phase:
            return None
        self._last_phase = current

        message = DUSK_MESSAGE if current == "night" else DAWN_MESSAGE
        await self._broadcast_to_outdoors(
            message, sio, online_sessions, game_state, utils
        )

        if mob_manager is not None:
            if current == "night":
                self._spawn_night_mobs(game_state, mob_manager)
            else:
                self._despawn_night_mobs(game_state, mob_manager)
        return current

    async def _broadcast_to_outdoors(
        self,
        message: str,
        sio: Any,
        online_sessions: Dict[str, Dict[str, Any]],
        game_state: Any,
        utils: Any,
    ) -> None:
        for sid, session in online_sessions.items():
            player = session.get("player")
            if not player or session.get("sleeping"):
                continue
            room = game_state.get_room(player.current_room)
            if room is not None and getattr(room, "is_outdoor", False):
                await utils.send_message(sio, sid, message)

    def _spawn_night_mobs(self, game_state: Any, mob_manager: Any) -> None:
        from managers.mob_definitions import NIGHT_SPAWNS

        for definition_id, room_id in NIGHT_SPAWNS:
            mob = mob_manager.spawn_mob(definition_id, room_id, game_state)
            if mob:
                self._night_mob_ids.append(mob.id)
                # Night creatures never respawn on a timer — slain ones stay
                # gone until the next dusk brings a fresh wave.
                mob_manager.spawn_records.pop(mob.id, None)

    def _despawn_night_mobs(self, game_state: Any, mob_manager: Any) -> None:
        for mob_id in self._night_mob_ids:
            # Survivors dissipate; slain ones are already gone (and must not
            # respawn in daylight, hence schedule_respawn=False on despawn).
            mob_manager.remove_mob(mob_id, game_state, schedule_respawn=False)
        self._night_mob_ids = []


# Module-global accessor, mirroring affliction_service.set_context.
_world_clock: Optional[WorldClock] = None


def set_world_clock(clock: Optional[WorldClock]) -> None:
    global _world_clock
    _world_clock = clock


def get_world_clock() -> Optional[WorldClock]:
    return _world_clock
