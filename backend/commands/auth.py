# backend/commands/auth.py

from typing import Any, Dict
from commands.registry import command_registry
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def handle_password(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    sio: Any,
    utils: Any,
) -> str:
    """
    Handle changing a player's password.
    """
    # Get the current sid from the online_sessions
    current_sid = None
    for sid, session in online_sessions.items():
        if session.get("player") == player:
            current_sid = sid
            break

    if not current_sid:
        return "Error: Session not found"

    # Get the original command text passed into the function
    command_text = cmd.get("original", "")

    # Initialize or get the password change state in the session
    if "pwd_change" not in online_sessions[current_sid]:
        online_sessions[current_sid]["pwd_change"] = {
            "stage": "old_password",
            "old_password": None,
            "new_password": None,
        }
        await utils.send_message(sio, current_sid, "What is your present password?")
        await sio.emit("setInputType", "password", room=current_sid)
        return ""  # Empty string because we already sent a message

    # Get the password change state
    pwd_change = online_sessions[current_sid]["pwd_change"]

    # Handle the password change stages
    if pwd_change["stage"] == "old_password":
        # Don't allow empty passwords
        if not command_text.strip():
            await utils.send_message(
                sio,
                current_sid,
                "Password cannot be blank. What is your present password?",
            )
            return ""

        # Validate the old password
        try:
            auth_manager = (
                player_manager.auth_manager
                if hasattr(player_manager, "auth_manager")
                else None
            )

            # If auth_manager is not available through player_manager, we might need a different approach
            # For now, assume it's accessible (you might need to adjust this part)
            if not auth_manager:
                from managers.auth import AuthManager

                auth_manager = AuthManager()

            auth_manager.login(player.name, command_text)
            pwd_change["old_password"] = command_text
            pwd_change["stage"] = "new_password"

            # Prompt for new password
            await utils.send_message(sio, current_sid, "\nNew password for persona.")
            await sio.emit("setInputType", "password", room=current_sid)

        except Exception:
            del online_sessions[current_sid]["pwd_change"]
            await sio.emit("setInputType", "text", room=current_sid)
            return "Incorrect, sorry. Password remains unchanged."

    elif pwd_change["stage"] == "new_password":
        # Store the new password
        new_password = command_text.strip()

        # Don't allow empty passwords
        if not new_password:
            await utils.send_message(
                sio,
                current_sid,
                "Password cannot be blank. Please enter a new password:",
            )
            return ""

        pwd_change["new_password"] = new_password
        pwd_change["stage"] = "confirm_password"

        # Prompt for password confirmation
        await utils.send_message(
            sio, current_sid, "\nEnter it again to make sure it's correct, please."
        )
        await sio.emit("setInputType", "password", room=current_sid)

    elif pwd_change["stage"] == "confirm_password":
        # Validate the password confirmation
        confirm_password = command_text.strip()

        # Don't allow empty confirmation
        if not confirm_password:
            await utils.send_message(
                sio,
                current_sid,
                "Password confirmation cannot be blank. Please confirm your password:",
            )
            return ""

        if confirm_password == pwd_change["new_password"]:
            # Update the password
            try:
                auth_manager = (
                    player_manager.auth_manager
                    if hasattr(player_manager, "auth_manager")
                    else None
                )

                # If auth_manager is not available, create one (adjust if needed)
                if not auth_manager:
                    from managers.auth import AuthManager

                    auth_manager = AuthManager()

                # Store original username for registration
                username = player.name.lower()

                # Attempt to update the password
                # Since there might not be a direct "change_password" method,
                # we might need to register with the same username and new password
                auth_manager.credentials[username] = auth_manager.hash_password(
                    username, pwd_change["new_password"]
                )
                auth_manager.save_credentials()

                # Clear the password change state
                del online_sessions[current_sid]["pwd_change"]

                # Reset input type to text
                await sio.emit("setInputType", "text", room=current_sid)

                return "Password changed successfully."

            except Exception as e:
                logger.error(f"Failed to change password: {str(e)}")
                del online_sessions[current_sid]["pwd_change"]
                await sio.emit("setInputType", "text", room=current_sid)
                return "Error changing password. Please try again later."
        else:
            # Passwords don't match
            del online_sessions[current_sid]["pwd_change"]
            await sio.emit("setInputType", "text", room=current_sid)
            return "No, they're different - password remains unchanged."

    return ""  # Empty string because we've already sent the appropriate messages


# Register the password command
command_registry.register("password", handle_password, "Change your account password.")


# Let's handle the case where the user might enter the password as a new command
async def handle_password_input(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    sio: Any,
    utils: Any,
) -> str:
    """
    This is a special handler for inputs during a password change process.
    It simply echoes back the password command to keep the flow in the password handler.
    """
    # This just ensures we correctly route back to the password handler
    current_sid = None
    for sid, session in online_sessions.items():
        if session.get("player") == player:
            current_sid = sid
            break

    if current_sid and "pwd_change" in online_sessions[current_sid]:
        # Redirect the flow to the password handler with the original text
        new_cmd = {"verb": "password", "original": cmd.get("original", "")}
        return await handle_password(
            new_cmd, player, game_state, player_manager, online_sessions, sio, utils
        )
    return "Type 'password' to change your password."
