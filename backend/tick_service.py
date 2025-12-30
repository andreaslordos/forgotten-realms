# backend/tick_service.py

"""Background tick service for realtime gameplay coordination."""

import asyncio
import logging
import time
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple, cast

from commands.combat import process_combat_tick
from commands.communication import handle_pending_communication
from commands.executor import execute_command
from commands.parser import parse_command_wrapper
from commands.rest import process_sleeping_players
from services.notifications import broadcast_logout


logger = logging.getLogger(__name__)


COMBAT_TICK_INTERVAL = 3.0  # Combat actions occur every 3 seconds
DEFAULT_TICK_INTERVAL = 0.5
INACTIVITY_RESET_SECONDS = 120 * 30  # Matches legacy behaviour (logged as 2 hours)
ERROR_RETRY_DELAY = 1.0


TimeFunc = Callable[[], float]
SleepFunc = Callable[[float], Awaitable[None]]


class TickService:
    """Coordinates periodic game ticks in an injectable, testable form."""

    def __init__(
        self,
        sio: Any,
        online_sessions: Dict[str, Dict[str, Any]],
        player_manager: Any,
        game_state: Any,
        utils: Any,
        *,
        time_func: Optional[TimeFunc] = None,
        sleep_func: Optional[SleepFunc] = None,
        combat_tick_interval: float = COMBAT_TICK_INTERVAL,
        tick_interval: float = DEFAULT_TICK_INTERVAL,
        inactivity_reset_seconds: float = INACTIVITY_RESET_SECONDS,
        parse_command: Any = parse_command_wrapper,
        execute_command: Any = execute_command,
        handle_pending_communication: Any = handle_pending_communication,
        combat_tick_callable: Any = process_combat_tick,
        sleeping_players_callable: Any = process_sleeping_players,
        broadcast_logout_callable: Any = broadcast_logout,
    ) -> None:
        self.sio = sio
        self.online_sessions = online_sessions
        self.player_manager = player_manager
        self.game_state = game_state
        self.utils = utils

        self._time: TimeFunc = time_func or time.time
        self._sleep: SleepFunc = sleep_func or asyncio.sleep

        self.combat_tick_interval = combat_tick_interval
        self.tick_interval = tick_interval
        self.inactivity_reset_seconds = inactivity_reset_seconds

        self.parse_command = parse_command
        self.execute_command = execute_command
        self.handle_pending_communication = handle_pending_communication
        self.combat_tick_callable = combat_tick_callable
        self.sleeping_players_callable = sleeping_players_callable
        self.broadcast_logout_callable = broadcast_logout_callable

        now = self._time()
        self._last_activity = now
        self._last_combat_tick = now

    async def run_forever(self) -> None:
        """Run the background tick loop indefinitely, handling errors resiliently."""
        logger.info("Background tick service running")
        while True:
            try:
                await self._sleep(self.tick_interval)
                await self.tick_once()
            except Exception as exc:  # pragma: no cover - defensive guard
                logger.error("Critical background tick error: %s", exc, exc_info=True)
                print(f"[Error] Critical background tick error: {str(exc)}")
                await self._sleep(ERROR_RETRY_DELAY)

    async def tick_once(self) -> None:
        """Execute a single tick worth of work without any sleeping."""
        current_time = self._time()

        await self._handle_inactivity_reset(current_time)
        await self._maybe_process_combat(current_time)
        await self._process_mob_ai()
        await self.sleeping_players_callable(
            self.sio, self.online_sessions, self.player_manager, self.utils
        )

        # Process affliction expiry
        await self._process_affliction_expiry()

        if not self.online_sessions:
            return

        for sid, session in list(self.online_sessions.items()):
            self._update_last_activity(session, current_time)

            command_queue: Optional[List[str]] = session.get("command_queue")
            if not command_queue:
                continue

            player = session.get("player")
            if not player:
                continue

            await self._process_player_command(sid, session, player, command_queue)

    async def _handle_inactivity_reset(self, current_time: float) -> None:
        if not self.online_sessions:
            return

        if current_time - self._last_activity > self.inactivity_reset_seconds:
            print("[Tick] Triggering inactivity reset after 2 hours...")
            logger.info("Triggering inactivity reset after 2 hours")
            # TODO: Implement mid-week reset here
            self._last_activity = current_time

    async def _maybe_process_combat(self, current_time: float) -> None:
        if current_time - self._last_combat_tick < self.combat_tick_interval:
            return

        mob_manager = self._get_mob_manager()
        await self.combat_tick_callable(
            self.sio,
            self.online_sessions,
            self.player_manager,
            self.game_state,
            self.utils,
            mob_manager,
        )
        self._last_combat_tick = current_time

    async def _process_mob_ai(self) -> None:
        mob_manager = self._get_mob_manager()
        if mob_manager:
            await mob_manager.tick_all_mobs(
                self.sio,
                self.online_sessions,
                self.player_manager,
                self.game_state,
                self.utils,
            )

    async def _process_affliction_expiry(self) -> None:
        """Process affliction expiration for all players."""
        from services.affliction_service import process_affliction_expiry

        await process_affliction_expiry(
            self.sio,
            self.online_sessions,
            self.utils,
        )

    def _get_mob_manager(self) -> Any:
        return getattr(self.utils, "mob_manager", None)

    def _update_last_activity(
        self, session: Dict[str, Any], current_time: float
    ) -> None:
        if session.get("command_queue") or session.get("player"):
            self._last_activity = current_time

    async def _process_player_command(
        self, sid: str, session: Dict[str, Any], player: Any, command_queue: List[str]
    ) -> None:
        cmd_str = command_queue.pop(0)
        logger.info(
            "Processing command: %s for player %s",
            cmd_str,
            getattr(player, "name", "unknown"),
        )

        try:
            if await self._handle_sleeping_player(sid, session, cmd_str):
                return

            if await self._handle_password_change(sid, session, player, cmd_str):
                return

            if await self._handle_pending_communication(sid, session, player, cmd_str):
                return

            cmd_str, skip_processing = await self._handle_converse_mode(
                sid, session, cmd_str
            )
            if skip_processing:
                return

            parsed_cmds = self._parse_command(cmd_str, session, player)

            if len(parsed_cmds) > 1:
                await self.utils.send_message(self.sio, sid, f"{cmd_str}")
                first_cmd = parsed_cmds[0]
                for i in range(len(parsed_cmds) - 1, 0, -1):
                    cmd_to_requeue = parsed_cmds[i].get("original", "")
                    if cmd_to_requeue:
                        command_queue.insert(0, cmd_to_requeue)
                parsed_cmds = [first_cmd]

            cmd = parsed_cmds[0] if parsed_cmds else None
            if not cmd:
                await self.utils.send_message(
                    self.sio, sid, "Huh? I didn't understand that."
                )
                return

            if len(parsed_cmds) <= 1:
                await self.utils.send_message(
                    self.sio, sid, f"{cmd.get('original', cmd_str)}"
                )

            result = await self.execute_command(
                cmd,
                player,
                self.game_state,
                self.player_manager,
                self.online_sessions,
                self.sio,
                self.utils,
                player_sid=sid,
            )

            if result:
                await self.utils.send_message(self.sio, sid, result)

            if result == "quit":
                session["should_disconnect"] = True
        except Exception as exc:
            logger.error(
                "Command '%s' failed for %s: %s",
                cmd_str,
                getattr(player, "name", "unknown"),
                exc,
                exc_info=True,
            )
            print(f"[Error] Command '{cmd_str}' failed for {player.name}: {str(exc)}")
            await self.utils.send_message(
                self.sio, sid, f"Error processing command: {str(exc)}"
            )
        finally:
            await self._send_stats_and_handle_disconnect(sid, session, player)

    async def _handle_sleeping_player(
        self, sid: str, session: Dict[str, Any], cmd_str: str
    ) -> bool:
        if not session.get("sleeping", False):
            return False

        lowered = cmd_str.lower()
        if lowered in ("wake", "awake"):
            return False

        await self.utils.send_message(self.sio, sid, "You are asleep.")
        return True

    async def _handle_password_change(
        self, sid: str, session: Dict[str, Any], player: Any, cmd_str: str
    ) -> bool:
        if "pwd_change" not in session:
            return False

        from commands.auth import handle_password  # Local import to avoid cycles

        pwd_cmd = {"verb": "password", "original": cmd_str}
        result = await handle_password(
            pwd_cmd,
            player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )
        if result:
            await self.utils.send_message(self.sio, sid, result)
        return True

    async def _handle_pending_communication(
        self, sid: str, session: Dict[str, Any], player: Any, cmd_str: str
    ) -> bool:
        pending_comm = session.get("pending_comm")
        if not pending_comm:
            return False

        pending_result = await self.handle_pending_communication(
            pending_comm,
            cmd_str,
            player,
            sid,
            self.online_sessions,
            self.sio,
            self.utils,
        )
        await self.utils.send_message(self.sio, sid, pending_result)
        return True

    async def _handle_converse_mode(
        self, sid: str, session: Dict[str, Any], cmd_str: str
    ) -> Tuple[str, bool]:
        if not session.get("converse_mode"):
            return cmd_str, False

        if cmd_str.startswith("*") or cmd_str.startswith(">"):
            session["converse_mode"] = False
            await self.utils.send_message(self.sio, sid, "Converse mode OFF.")
            return cmd_str, True

        # Prepend "say" and continue in converse mode
        return f"say {cmd_str}", False

    def _parse_command(
        self, cmd_str: str, session: Dict[str, Any], player: Any
    ) -> List[Dict[str, Any]]:
        mob_manager = self._get_mob_manager()
        players_in_room = []

        if self.online_sessions:
            for osid, osession in self.online_sessions.items():
                other_player = osession.get("player")
                if other_player and other_player.current_room == player.current_room:
                    players_in_room.append(other_player)

        context = {
            "player": player,
            "game_state": self.game_state,
            "online_sessions": self.online_sessions,
            "mob_manager": mob_manager,
            "players_in_room": players_in_room,
        }

        result = self.parse_command(
            cmd_str,
            context=context,
            players_in_room=players_in_room,
            online_sessions=self.online_sessions,
        )
        return cast(List[Dict[str, Any]], result)

    async def _send_stats_and_handle_disconnect(
        self, sid: str, session: Dict[str, Any], player: Any
    ) -> None:
        if player:
            await self.utils.send_stats_update(self.sio, sid, player)

        if session.get("should_disconnect"):
            try:
                await self.sio.disconnect(sid)
                await self.broadcast_logout_callable(player)
            except Exception as exc:
                logger.error(
                    "Failed to disconnect %s: %s",
                    getattr(player, "name", "unknown"),
                    exc,
                    exc_info=True,
                )
                print(f"[Error] Failed to disconnect {player.name}: {str(exc)}")


async def start_background_tick(
    sio: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    player_manager: Any,
    game_state: Any,
    utils: Any,
) -> None:
    """Legacy entry point retained for backwards compatibility."""
    print("[Tick] Background tick service starting...")
    logger.info("Background tick service starting")

    service = TickService(
        sio,
        online_sessions,
        player_manager,
        game_state,
        utils,
    )

    await service.run_forever()
