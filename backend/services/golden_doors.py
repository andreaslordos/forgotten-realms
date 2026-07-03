# backend/services/golden_doors.py
"""
Golden doors: extremely rare sealed doors hiding AI-generated pocket
dimensions.

Opening one takes BOTH the golden key (an ultra-rare drop) and speaking the
door's riddle answer aloud in its room. The first successful opening
generates the dimension (Claude via services.zone_generator, validated by
services.zone_schema, with a hand-authored fallback) and attaches it for
every player until the world resets. One generation per door per reset.

The door's open interaction runs synchronously inside the tick loop, so it
only kicks off an asyncio task and returns flavor text; the door swings open
(or the light gutters out) when the task completes.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set

from models.StatefulItem import StatefulItem

logger = logging.getLogger(__name__)

GOLDEN_KEY_ID = "golden_key"

OPENING_MESSAGE = (
    "The golden key sinks into a keyhole that was not there a heartbeat ago. "
    "The door GROANS, and molten light spills through the widening seam..."
)
OPEN_BROADCAST = (
    "The golden door swings fully open. Beyond it lies somewhere that "
    "should not exist."
)
FAILURE_BROADCAST = (
    "The molten light gutters and dies. The golden door is merely a door "
    "again... for now."
)


@dataclass
class GoldenDoorState:
    door_id: str
    room_id: str
    theme_hint: str
    riddle_answer: str
    status: str = "sealed"  # sealed | opening | open
    riddle_spoken: bool = False
    door_item: Optional[StatefulItem] = field(default=None, repr=False)


DOOR_REGISTRY: Dict[str, GoldenDoorState] = {}

# Strong references to in-flight generation tasks: an un-referenced asyncio
# task can be garbage-collected mid-flight, which would leave a door stuck
# in 'opening' forever.
_generation_tasks: Set["asyncio.Task[None]"] = set()


def reset_doors() -> None:
    """Forget all doors (world reset / tests)."""
    DOOR_REGISTRY.clear()


def _consume_golden_key(player: Any) -> None:
    for item in list(player.inventory):
        if getattr(item, "id", None) == GOLDEN_KEY_ID:
            player.remove_item(item)
            return


async def _generate_and_open(
    door_id: str,
    player: Any,
    game_state: Any,
    generator: Any,
) -> None:
    """Background task: generate, validate, inject; open or reseal the door."""
    from services.notifications import broadcast_room

    state = DOOR_REGISTRY.get(door_id)
    if state is None:
        return
    try:
        opened = await _try_open(state, door_id, player, game_state, generator)
    except Exception:  # never let a generation crash linger silently
        logger.exception("Golden door %s generation crashed", door_id)
        opened = False
    if not opened:
        state.status = "sealed"
        if state.door_item is not None:
            state.door_item.set_state("sealed", game_state)
        await broadcast_room(state.room_id, FAILURE_BROADCAST)


async def _try_open(
    state: GoldenDoorState,
    door_id: str,
    player: Any,
    game_state: Any,
    generator: Any,
) -> bool:
    from services.notifications import broadcast_room
    from services.zone_generator import load_fallback_spec
    from services.zone_injector import inject_zone
    from services.zone_schema import validate_zone_spec

    prefix = f"pd_{door_id}_"
    spec: Optional[Dict[str, Any]] = None
    existing_ids = set(game_state.rooms.keys())
    avoid_names = [room.name for room in list(game_state.rooms.values())[:60]]

    if generator is not None and generator.is_available():
        errors: list[str] = []
        for _attempt in range(2):
            try:
                candidate = await generator.generate_zone_spec(
                    state.theme_hint,
                    avoid_names=avoid_names,
                    previous_errors=errors or None,
                )
            except Exception:
                logger.exception("Zone generation attempt failed for %s", door_id)
                continue
            errors = validate_zone_spec(candidate, prefix, existing_ids)
            if not errors:
                spec = candidate
                break
            logger.warning("Generated zone rejected for %s: %s", door_id, errors)

    if spec is None:
        fallback = load_fallback_spec()
        if fallback is not None and not validate_zone_spec(
            fallback, prefix, existing_ids
        ):
            spec = fallback

    if spec is None:
        return False

    import utils as utils_module

    mob_manager = getattr(utils_module, "mob_manager", None)
    inject_zone(spec, prefix, game_state, mob_manager, state.room_id)

    state.status = "open"
    if state.door_item is not None:
        state.door_item.set_state("open", game_state)
    _consume_golden_key(player)
    await broadcast_room(state.room_id, OPEN_BROADCAST)
    logger.info("Golden door %s opened onto '%s'", door_id, spec.get("zone_name"))
    return True


def make_open_effect(door_id: str, generator_factory: Any = None) -> Any:
    """
    Build the sync effect_fn for the door's open interaction. It flips the
    door to 'opening' and schedules the generation task.
    """

    def effect(player: Any, game_state: Any) -> Optional[str]:
        state = DOOR_REGISTRY.get(door_id)
        if state is None or state.status != "sealed":
            return None
        state.status = "opening"

        generator = None
        if generator_factory is not None:
            generator = generator_factory()
        else:
            from services.zone_generator import ZoneGenerator

            generator = ZoneGenerator()

        task = asyncio.get_running_loop().create_task(
            _generate_and_open(door_id, player, game_state, generator)
        )
        _generation_tasks.add(task)
        task.add_done_callback(_generation_tasks.discard)
        return OPENING_MESSAGE

    return effect


def create_golden_door(
    door_id: str,
    room: Any,
    theme_hint: str,
    riddle_text: str,
    riddle_answer: str,
    generator_factory: Any = None,
) -> StatefulItem:
    """
    Create a golden door in `room`: registers its state, its riddle speech
    trigger, and the door StatefulItem with all interactions wired.
    """
    state = GoldenDoorState(
        door_id=door_id,
        room_id=room.room_id,
        theme_hint=theme_hint,
        riddle_answer=riddle_answer.lower(),
    )
    DOOR_REGISTRY[door_id] = state

    door = StatefulItem(
        name="golden door",
        id=f"golden_door_{door_id}",
        description=(
            "A door of solid gold stands here, seamless and lockless, "
            "radiating a warmth the stone around it does not share."
        ),
        takeable=False,
        state="sealed",
        room_id=room.room_id,
        synonyms=["door", "gold door", "golden"],
    )
    door.add_state_description(
        "sealed",
        "A door of solid gold stands here, seamless and lockless, radiating "
        "a warmth the stone around it does not share.",
    )
    door.add_state_description(
        "opening",
        "The golden door stands ajar, molten light pouring through the seam.",
    )
    door.add_state_description(
        "open",
        "The golden door stands open. Somewhere else breathes beyond it.",
    )

    def riddle_spoken(player: Any, game_state: Any) -> bool:
        return state.riddle_spoken

    door.add_interaction(
        verb="open",
        from_state="sealed",
        target_state="opening",
        required_instrument=GOLDEN_KEY_ID,
        conditional_fn=riddle_spoken,
        effect_fn=make_open_effect(door_id, generator_factory),
    )
    door.add_interaction(
        verb="open",
        from_state="sealed",
        message=(
            "There is no handle, no hinge, no lock — yet a hair-thin seam "
            "runs down the center. Etched above it, almost too faint to "
            f"read: {riddle_text}"
        ),
    )
    door.add_interaction(
        verb="open",
        from_state="opening",
        message="Molten light already pours through the widening seam. Wait.",
    )
    door.add_interaction(
        verb="examine",
        message=(
            "The gold is warm and utterly seamless — no key forged by man "
            f"should fit it. Etched above the seam: {riddle_text}"
        ),
    )

    def mark_riddle_spoken(player: Any, game_state: Any) -> bool:
        # conditional_fn used for its side effect gate: only fires pre-open
        return not state.riddle_spoken and state.status == "sealed"

    async def riddle_effect(
        player: Any,
        game_state: Any,
        player_manager: Any,
        online_sessions: Any,
        sio: Any,
        utils: Any,
    ) -> None:
        state.riddle_spoken = True

    room.add_speech_trigger(
        keyword=state.riddle_answer,
        message=(
            "The golden door SHIVERS. For a moment the seam glows like a "
            "sunrise — it has heard you. It wants a key."
        ),
        conditional_fn=mark_riddle_spoken,
        effect_fn=riddle_effect,
        one_time=False,
    )

    state.door_item = door
    room.add_item(door)
    return door
