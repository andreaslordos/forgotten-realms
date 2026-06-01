"""HTTP routes for the admin world builder."""

import json
import secrets
import shlex
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from aiohttp import web

ADMIN_USERNAME = "stupidgem"


def create_admin_token() -> str:
    """Create an opaque bearer token for an authenticated admin session."""
    return secrets.token_urlsafe(32)


def is_admin_session(session: Dict[str, Any]) -> bool:
    """Return whether a Socket.IO session belongs to the hardcoded admin."""
    player = session.get("player")
    player_name = getattr(player, "name", "")
    return player_name.lower() == ADMIN_USERNAME


def _extract_token(request: Any) -> Optional[str]:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[len("Bearer ") :].strip()
        return token or None
    token = request.headers.get("X-Admin-Token")
    return token or None


def _find_admin_session(
    online_sessions: Dict[str, Dict[str, Any]], token: Optional[str]
) -> Optional[Dict[str, Any]]:
    if not token:
        return None

    for session in online_sessions.values():
        if session.get("admin_token") == token and is_admin_session(session):
            return session
    return None


def _cors_headers() -> Dict[str, str]:
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Authorization, Content-Type, X-Admin-Token",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    }


def _json_response(payload: Dict[str, Any], status: int = 200) -> web.Response:
    response = web.json_response(payload, status=status)
    for key, value in _cors_headers().items():
        response.headers[key] = value
    return response


def _error_response(error: str, message: str, status: int) -> web.Response:
    return _json_response({"error": error, "message": message}, status=status)


class AdminRouteController:
    """Request handlers for admin world-builder APIs."""

    def __init__(
        self,
        game_state: Any,
        mob_manager: Any,
        online_sessions: Dict[str, Dict[str, Any]],
        world_builder: Any,
        world_factory: Callable[..., Dict[str, Any]],
        publish_checks: Optional[List[str]] = None,
    ) -> None:
        self.game_state = game_state
        self.mob_manager = mob_manager
        self.online_sessions = online_sessions
        self.world_builder = world_builder
        self.world_factory = world_factory
        self.publish_checks = publish_checks or []

    def _require_admin(self, request: Any) -> Optional[web.Response]:
        session = _find_admin_session(self.online_sessions, _extract_token(request))
        if session:
            return None
        return _error_response(
            "unauthorized",
            "You must be logged in as stupidgem to use the world builder.",
            401,
        )

    async def _read_world(self, request: Any) -> Any:
        try:
            payload = await request.json()
        except json.JSONDecodeError:
            return _error_response("invalid_json", "Request body must be JSON.", 400)

        world_data = payload.get("world") if isinstance(payload, dict) else None
        if not isinstance(world_data, dict):
            return _error_response(
                "invalid_world",
                "Request body must include a world object.",
                400,
            )
        return world_data

    def _spawn_room(self) -> Optional[str]:
        return getattr(self.game_state, "spawn_room", None) or "square"

    async def options(self, request: Any) -> web.Response:
        return _json_response({}, status=204)

    async def session(self, request: Any) -> web.Response:
        admin_session = _find_admin_session(self.online_sessions, _extract_token(request))
        if not admin_session:
            return _json_response({"admin": False})
        player = admin_session.get("player")
        return _json_response(
            {"admin": True, "player": getattr(player, "name", ADMIN_USERNAME)}
        )

    async def get_world(self, request: Any) -> web.Response:
        unauthorized = self._require_admin(request)
        if unauthorized is not None:
            return unauthorized

        world_data = self.world_builder.load_or_export()
        return _json_response({"world": world_data})

    async def save_world(self, request: Any) -> web.Response:
        unauthorized = self._require_admin(request)
        if unauthorized is not None:
            return unauthorized

        world_data = await self._read_world(request)
        if isinstance(world_data, web.Response):
            return world_data

        validation = self._validation_to_dict(self.world_builder.validate(world_data))
        if not validation.get("ok", False):
            return _json_response(
                {"error": "validation_failed", "validation": validation},
                status=400,
            )

        save_result = self.world_builder.save(world_data)
        return _json_response({"saved": save_result, "validation": validation})

    async def validate_world(self, request: Any) -> web.Response:
        unauthorized = self._require_admin(request)
        if unauthorized is not None:
            return unauthorized

        world_data = await self._read_world(request)
        if isinstance(world_data, web.Response):
            return world_data

        validation = self._validation_to_dict(self.world_builder.validate(world_data))
        return _json_response({"validation": validation})

    async def apply_world(self, request: Any) -> web.Response:
        unauthorized = self._require_admin(request)
        if unauthorized is not None:
            return unauthorized

        world_data = await self._read_world(request)
        if isinstance(world_data, web.Response):
            return world_data

        validation = self._validation_to_dict(self.world_builder.validate(world_data))
        if not validation.get("ok", False):
            return _json_response(
                {"error": "validation_failed", "validation": validation},
                status=400,
            )

        save_result = self.world_builder.save(world_data)
        apply_validation = self._validation_to_dict(self.world_builder.apply(world_data))
        if not apply_validation.get("ok", False):
            return _json_response(
                {"error": "validation_failed", "validation": apply_validation},
                status=400,
            )
        return _json_response(
            {
                "saved": save_result,
                "applied": self._apply_summary(world_data),
                "validation": validation,
            }
        )

    async def reset_world(self, request: Any) -> web.Response:
        unauthorized = self._require_admin(request)
        if unauthorized is not None:
            return unauthorized

        world_data = self.world_builder.reset_from_baseline(self.world_factory)
        return _json_response({"world": world_data})

    async def publish_world(self, request: Any) -> web.Response:
        unauthorized = self._require_admin(request)
        if unauthorized is not None:
            return unauthorized

        world_data = await self._read_world(request)
        if isinstance(world_data, web.Response):
            return world_data

        validation = self._validation_to_dict(self.world_builder.validate(world_data))
        if not validation.get("ok", False):
            return _json_response(
                {"error": "validation_failed", "validation": validation},
                status=400,
            )

        save_result = self.world_builder.save(world_data)
        publish_result = self.world_builder.publish(
            world_data, checks=self._publish_checks(), message="Publish world data"
        )
        publish_payload = self._publish_to_dict(publish_result)
        if not self._publish_ok(publish_payload):
            message = (
                publish_payload.get("error")
                or publish_payload.get("output")
                or "World publish failed."
            )
            return _json_response(
                {
                    "error": "publish_failed",
                    "message": message,
                    "saved": save_result,
                    "publish": publish_payload,
                    "validation": validation,
                },
                status=500,
            )
        return _json_response(
            {
                "saved": save_result,
                "publish": publish_payload,
                "validation": validation,
            }
        )

    def _validation_to_dict(self, validation: Any) -> Dict[str, Any]:
        if hasattr(validation, "to_dict"):
            return validation.to_dict()
        return validation

    def _publish_to_dict(self, publish_result: Any) -> Dict[str, Any]:
        if hasattr(publish_result, "to_dict"):
            data = publish_result.to_dict()
            data.setdefault("committed", bool(data.get("ok")))
            data.setdefault("pushed", bool(data.get("ok")))
            return data
        return publish_result

    def _publish_ok(self, publish_payload: Dict[str, Any]) -> bool:
        if "ok" in publish_payload:
            return bool(publish_payload.get("ok"))
        return bool(publish_payload.get("pushed") or publish_payload.get("committed"))

    def _publish_checks(self) -> List[List[str]]:
        normalized: List[List[str]] = []
        for check in self.publish_checks:
            if isinstance(check, str):
                normalized.append(shlex.split(check))
            else:
                normalized.append(list(check))
        return normalized

    def _apply_summary(self, world_data: Dict[str, Any]) -> Dict[str, int]:
        return {
            "rooms": len(world_data.get("rooms", [])),
            "mobs": len(world_data.get("mobs", [])),
        }


def register_admin_routes(
    app: web.Application,
    game_state: Any,
    mob_manager: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    world_factory: Callable[..., Dict[str, Any]],
    world_builder: Optional[Any] = None,
    publish_checks: Optional[List[str]] = None,
) -> AdminRouteController:
    """Register admin world-builder routes on the aiohttp app."""
    if world_builder is None:
        from admin.world_builder import WorldBuilder

        backend_dir = Path(__file__).resolve().parents[1]
        repo_dir = backend_dir.parent
        world_builder = WorldBuilder(
            game_state=game_state,
            mob_manager=mob_manager,
            data_path=backend_dir / "storage" / "world_builder" / "draft_world.json",
            repo_path=repo_dir,
            spawn_room_id="square",
        )

    controller = AdminRouteController(
        game_state=game_state,
        mob_manager=mob_manager,
        online_sessions=online_sessions,
        world_builder=world_builder,
        world_factory=world_factory,
        publish_checks=publish_checks,
    )

    routes = {
        "/admin/api/session": {
            "GET": controller.session,
        },
        "/admin/api/world": {
            "GET": controller.get_world,
            "POST": controller.save_world,
        },
        "/admin/api/world/validate": {
            "POST": controller.validate_world,
        },
        "/admin/api/world/apply": {
            "POST": controller.apply_world,
        },
        "/admin/api/world/reset": {
            "POST": controller.reset_world,
        },
        "/admin/api/world/publish": {
            "POST": controller.publish_world,
        },
    }

    for path, methods in routes.items():
        app.router.add_route("OPTIONS", path, controller.options)
        for method, handler in methods.items():
            app.router.add_route(method, path, handler)

    return controller
