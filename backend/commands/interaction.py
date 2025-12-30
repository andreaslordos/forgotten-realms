# backend/commands/interaction.py

from commands.registry import command_registry
from typing import Any, Dict

from commands.executor import build_look_description
import logging
import traceback
from services.notifications import broadcast_room

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def handle_interaction(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    sio: Any,
    utils: Any,
) -> str:
    """
    Handle specific verb-object interactions with enhanced features:
    - Consuming items after use
    - Dropping items after use
    - Creating bidirectional exits
    - Support for both syntax formats
    """
    try:
        verb = cmd.get("verb")
        subject = cmd.get("subject")
        subject_obj = cmd.get("subject_object")
        instrument = cmd.get("instrument")
        instrument_obj = cmd.get("instrument_object")
        preposition = cmd.get("preposition", "with")
        reversed_syntax = cmd.get("reversed_syntax", False)

        if not subject and not subject_obj:
            return f"What do you want to {verb}?"

        # Initialize search variables
        primary_item = None
        secondary_item = None
        current_room = game_state.get_room(player.current_room)

        # If we have bound objects, use them directly
        if reversed_syntax:
            # In reversed syntax, the instrument is primary and subject is secondary
            if instrument_obj and hasattr(instrument_obj, "interactions"):
                primary_item = instrument_obj
                secondary_item = subject_obj
                if hasattr(primary_item, "set_room_id"):
                    primary_item.set_room_id(current_room.room_id)
            elif subject_obj and hasattr(subject_obj, "interactions"):
                # Fallback - maybe the subject is actually the interactable item
                primary_item = subject_obj
                secondary_item = instrument_obj
                if hasattr(primary_item, "set_room_id"):
                    primary_item.set_room_id(current_room.room_id)
        else:
            # In standard syntax, the subject is primary and instrument is secondary
            if subject_obj and hasattr(subject_obj, "interactions"):
                primary_item = subject_obj
                secondary_item = instrument_obj
                if hasattr(primary_item, "set_room_id"):
                    primary_item.set_room_id(current_room.room_id)

        # If no primary item found using bound objects, fall back to name-based search
        if not primary_item:
            if reversed_syntax:
                # In reversed syntax, first find the intended target in either:
                # 1. instrument field (which was originally the subject but is now in instrument field)
                # 2. subject field (if the reversal was incorrect)

                # Try to find the item with interactions in the room based on instrument field
                for item in current_room.get_items(game_state):
                    if (
                        instrument
                        and hasattr(item, "matches_name")
                        and item.matches_name(instrument)
                        and hasattr(item, "interactions")
                    ):
                        primary_item = item
                        secondary_item_name = subject  # The subject is actually the instrument in reversed syntax
                        if hasattr(primary_item, "set_room_id"):
                            primary_item.set_room_id(current_room.room_id)
                        break

                # If not found, check if subject is actually the item with interactions
                if not primary_item:
                    for item in current_room.get_items(game_state):
                        if (
                            subject
                            and hasattr(item, "matches_name")
                            and item.matches_name(subject)
                            and hasattr(item, "interactions")
                        ):
                            primary_item = item
                            secondary_item_name = (
                                instrument  # Keep the original instrument
                            )
                            if hasattr(primary_item, "set_room_id"):
                                primary_item.set_room_id(current_room.room_id)
                            break

                # If still not found, check player's inventory
                if not primary_item:
                    for item in player.inventory:
                        if (
                            instrument
                            and hasattr(item, "matches_name")
                            and item.matches_name(instrument)
                            and hasattr(item, "interactions")
                        ):
                            primary_item = item
                            secondary_item_name = subject
                            break

                # One last attempt with subject field
                if not primary_item:
                    for item in player.inventory:
                        if (
                            subject
                            and hasattr(item, "matches_name")
                            and item.matches_name(subject)
                            and hasattr(item, "interactions")
                        ):
                            primary_item = item
                            secondary_item_name = instrument
                            break
            else:
                # Standard syntax, subject contains the target item, instrument contains the tool

                # First check player inventory for subject
                for item in player.inventory:
                    if (
                        subject
                        and hasattr(item, "matches_name")
                        and item.matches_name(subject)
                        and hasattr(item, "interactions")
                    ):
                        primary_item = item
                        secondary_item_name = instrument
                        break

                # If not in inventory, check the room items
                if not primary_item:
                    for item in current_room.get_items(game_state):
                        if (
                            subject
                            and hasattr(item, "matches_name")
                            and item.matches_name(subject)
                            and hasattr(item, "interactions")
                        ):
                            primary_item = item
                            secondary_item_name = instrument
                            if hasattr(primary_item, "set_room_id"):
                                primary_item.set_room_id(current_room.room_id)
                            break

            # If we found a primary item using name-based search, and need to find secondary item by name
            if (
                primary_item
                and "secondary_item_name" in locals()
                and secondary_item_name
            ):
                for item in player.inventory:
                    if hasattr(item, "matches_name") and item.matches_name(
                        secondary_item_name
                    ):
                        secondary_item = item
                        break

        # If we couldn't find primary item with interactions
        if not primary_item:
            return f"You can't {verb} that."

        # If we found a primary item, but it doesn't support this verb
        if verb not in primary_item.interactions:
            return f"You can't {verb} the {primary_item.name}."

        # Get all possible interactions for this verb
        possible_interactions = primary_item.interactions[verb]

        # Make sure we're dealing with a list
        if not isinstance(possible_interactions, list):
            possible_interactions = [possible_interactions]  # Backward compatibility

        # Find the appropriate interaction based on current state and conditions
        valid_interaction = None
        for interaction in possible_interactions:
            # Skip non-dictionary interactions
            if not isinstance(interaction, dict):
                continue

            # Check if this interaction is valid for the current state
            if "from_state" in interaction:
                from_state = interaction["from_state"]
                if from_state is not None and from_state != primary_item.state:
                    continue

            # We found a match for the current state (or one with no state requirement)
            valid_interaction = interaction
            break

        # If no valid interaction was found
        if not valid_interaction:
            return f"You can't {verb} the {primary_item.name} in its current state."

        # If an instrument is required, check if we have it
        if (
            "required_instrument" in valid_interaction
            and valid_interaction["required_instrument"]
        ):
            required_instrument = valid_interaction["required_instrument"]

            if not secondary_item:
                return (
                    f"You need {required_instrument} to {verb} the {primary_item.name}."
                )

            # Check if it's the right type of instrument
            if required_instrument.lower() not in secondary_item.name.lower():
                return f"You can't {verb} the {primary_item.name} with that."

        # Check any additional conditions
        if (
            "conditional_fn" in valid_interaction
            and valid_interaction["conditional_fn"]
        ):
            if not valid_interaction["conditional_fn"](player, game_state):
                return f"You can't {verb} the {primary_item.name} right now."

        # All conditions met, perform the interaction

        # First, handle state change
        if "target_state" in valid_interaction and valid_interaction["target_state"]:
            target_state = valid_interaction["target_state"]
            primary_item.set_state(target_state, game_state)

            # Check if this state change should make the item emit light
            # Items in "lit" state emit light
            if target_state == "lit":
                primary_item.emits_light = True
            elif target_state == "unlit" or target_state == "extinguished":
                primary_item.emits_light = False

            # Broadcast state change to other players in the room
            if hasattr(primary_item, "room_id") and primary_item.room_id:
                # Create a message that describes what happened
                change_message = f"{player.name} {verb}s the {primary_item.name}."

                # Use the notifications service to broadcast
                await broadcast_room(
                    primary_item.room_id, change_message, exclude_player=[player.name]
                )

        # Handle removing the item if specified
        if valid_interaction.get("remove_item", False):
            if hasattr(primary_item, "room_id") and primary_item.room_id:
                room = game_state.get_room(primary_item.room_id)
                if room:
                    room.remove_item(primary_item)

        # Handle adding an exit
        if "add_exit" in valid_interaction:
            direction, target_room_id = valid_interaction["add_exit"]
            if current_room:
                current_room.exits[direction] = target_room_id

        # Handle removing an exit
        if "remove_exit" in valid_interaction:
            direction = valid_interaction["remove_exit"]
            if current_room and direction in current_room.exits:
                del current_room.exits[direction]

        # Handle the reciprocal exit (creating the return path)
        if "reciprocal_exit" in valid_interaction:
            source_room_id, direction, target_room_id = valid_interaction[
                "reciprocal_exit"
            ]
            source_room = game_state.get_room(source_room_id)
            if source_room:
                source_room.exits[direction] = target_room_id

        # Handle consuming the instrument
        if (
            "consume_instrument" in valid_interaction
            and valid_interaction["consume_instrument"]
            and secondary_item
        ):
            player.remove_item(secondary_item)
            # No need to add to room since it's consumed

        # Handle dropping the instrument
        if (
            "drop_instrument" in valid_interaction
            and valid_interaction["drop_instrument"]
            and secondary_item
        ):
            player.remove_item(secondary_item)
            current_room.add_item(secondary_item)

        # Save changes to player and game state
        player_manager.save_players()
        # game_state.save_rooms()  # Uncomment if you're saving rooms

        # Get the success message
        message = valid_interaction.get(
            "message", f"You {verb} the {primary_item.name}."
        )

        # For exit modifications, mention the new direction
        exit_msg = ""
        if "add_exit" in valid_interaction:
            direction, _ = valid_interaction["add_exit"]
            exit_msg = f" You can now go {direction}."

        # If requested, show the full room description
        if valid_interaction.get("show_room_desc", False):
            mob_manager = (
                getattr(utils, "mob_manager", None)
                if utils and hasattr(utils, "__dict__")
                else None
            )
            return f"{message}{exit_msg}\n\n{build_look_description(player, game_state, online_sessions, mob_manager=mob_manager)}"

        return f"{message}{exit_msg}"

    except Exception as e:
        error_trace = traceback.format_exc()
        logger.error(f"Exception in interaction handler: {e}")
        logger.error(error_trace)
        return f"Error processing command: {str(e)}"


# Register all the interaction verbs
common_interaction_verbs = [
    "open",
    "close",
    "push",
    "pull",
    "turn",
    "twist",
    "light",
    "extinguish",
    "touch",
    "place",
    "cut",
    "break",
    "chop",
    "hit",
    "move",
    "unlock",
    "lock",
    "knock",
    "read",
    "tie",
    "use",
    "kneel",
    "bow",
    "search",
]


def register_interaction_verbs() -> None:
    for verb in common_interaction_verbs:
        command_registry.register(
            verb,
            handle_interaction,
            f"{verb.capitalize()} something, optionally with an instrument.",
        )


# Call this function to register all verbs
register_interaction_verbs()
