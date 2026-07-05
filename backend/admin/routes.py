"""HTTP routes for the admin world builder."""

import json
import secrets
import shlex
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from aiohttp import web

from globals import SPAWN_ROOM
from managers.mob_definitions import get_mob_definitions
from models.Levels import levels
from models.Mobile import Mobile

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
        "Access-Control-Allow-Methods": "GET, POST, PATCH, DELETE, OPTIONS",
    }


def _json_response(payload: Dict[str, Any], status: int = 200) -> web.Response:
    response = web.json_response(payload, status=status)
    for key, value in _cors_headers().items():
        response.headers[key] = value
    return response


def _error_response(error: str, message: str, status: int) -> web.Response:
    return _json_response({"error": error, "message": message}, status=status)


# Mobile constructor parameters a definition may override. Anything absent
# falls back to the defaults declared on Mobile.__init__ itself, so the
# stat defaults live in exactly one place (models/Mobile.py).
_MOB_DEFINITION_STAT_FIELDS = (
    "strength",
    "dexterity",
    "max_stamina",
    "damage",
    "aggressive",
    "aggro_delay_min",
    "aggro_delay_max",
    "patrol_rooms",
    "movement_interval",
    "point_value",
    "pronouns",
    "instant_death",
)


def _serialize_mob_definition(
    definition_id: str, definition: Dict[str, Any]
) -> Dict[str, Any]:
    """Serialize a mob template, applying the Mobile model defaults.

    A throwaway Mobile is instantiated from the definition the same way
    MobManager.spawn_mob does, so unspecified stats pick up the defaults
    from Mobile.__init__ instead of a duplicated table here.
    """
    overrides = {
        field: definition[field]
        for field in _MOB_DEFINITION_STAT_FIELDS
        if field in definition
    }
    mob = Mobile(
        name=str(definition.get("name") or definition_id),
        id=definition_id,
        description=str(definition.get("description") or ""),
        **overrides,
    )
    loot_table: List[Dict[str, Any]] = []
    for entry in definition.get("loot_table") or []:
        if not isinstance(entry, dict):
            continue
        item = entry.get("item")
        if item is None or not hasattr(item, "to_dict"):
            continue
        loot_table.append(
            {"item": item.to_dict(), "chance": float(entry.get("chance", 0.0))}
        )
    return {
        "id": definition_id,
        "name": mob.name,
        "description": mob.description,
        "strength": int(mob.strength),
        "dexterity": int(mob.dexterity),
        "max_stamina": int(mob.max_stamina),
        "damage": int(mob.damage),
        "aggressive": bool(mob.aggressive),
        "aggro_delay_min": int(mob.aggro_delay_min),
        "aggro_delay_max": int(mob.aggro_delay_max),
        "movement_interval": int(mob.movement_interval),
        "patrol_rooms": [str(room_id) for room_id in mob.patrol_rooms],
        "point_value": int(mob.point_value),
        "pronouns": str(mob.pronouns),
        "instant_death": bool(mob.instant_death),
        "loot_table": loot_table,
    }


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

    async def _read_json(self, request: Any) -> Any:
        try:
            payload = await request.json()
        except json.JSONDecodeError:
            return _error_response("invalid_json", "Request body must be JSON.", 400)
        if not isinstance(payload, dict):
            return _error_response(
                "invalid_json", "Request body must be a JSON object.", 400
            )
        return payload

    async def options(self, request: Any) -> web.Response:
        return _json_response({}, status=204)

    async def session(self, request: Any) -> web.Response:
        admin_session = _find_admin_session(
            self.online_sessions, _extract_token(request)
        )
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
        payload = {"world": world_data}
        if hasattr(self.world_builder, "list_drafts"):
            manifest = self.world_builder.list_drafts()
            payload.update(manifest)
            active_draft_id = manifest.get("active_draft_id")
            for draft in manifest.get("drafts", []):
                if draft.get("id") == active_draft_id:
                    payload["draft"] = draft
                    break
        return _json_response(payload)

    async def list_mob_definitions(self, request: Any) -> web.Response:
        unauthorized = self._require_admin(request)
        if unauthorized is not None:
            return unauthorized

        definitions = get_mob_definitions()
        return _json_response(
            {
                "mob_definitions": [
                    _serialize_mob_definition(definition_id, definition)
                    for definition_id, definition in definitions.items()
                ],
                # Level names feed the weapon min-level dropdown; they live in
                # the same reference payload to avoid a second round trip.
                "levels": [stats["name"] for stats in levels.values()],
            }
        )

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
        apply_validation = self._validation_to_dict(
            self.world_builder.apply(world_data)
        )
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

    async def list_world_drafts(self, request: Any) -> web.Response:
        unauthorized = self._require_admin(request)
        if unauthorized is not None:
            return unauthorized

        return _json_response(self.world_builder.list_drafts())

    async def create_world_draft(self, request: Any) -> web.Response:
        unauthorized = self._require_admin(request)
        if unauthorized is not None:
            return unauthorized

        payload = await self._read_json(request)
        if isinstance(payload, web.Response):
            return payload
        try:
            result = self.world_builder.create_draft(
                name=str(payload.get("name") or "New Draft"),
                source=str(payload.get("source") or "active"),
                source_draft_id=payload.get("source_draft_id"),
                description=str(payload.get("description") or ""),
            )
        except KeyError as error:
            return _error_response("draft_not_found", str(error), 404)
        except ValueError as error:
            return _error_response("invalid_draft", str(error), 400)
        return _json_response(result)

    async def get_world_draft(
        self, request: Any, draft_id: Optional[str] = None
    ) -> web.Response:
        unauthorized = self._require_admin(request)
        if unauthorized is not None:
            return unauthorized

        effective_draft_id = self._request_draft_id(request, draft_id)
        try:
            loaded = self.world_builder.load_draft(effective_draft_id)
        except KeyError as error:
            return _error_response("draft_not_found", str(error), 404)
        except ValueError as error:
            return _error_response("invalid_draft", str(error), 400)
        if isinstance(loaded, dict) and "world" in loaded:
            return _json_response(loaded)
        return _json_response(
            {"world": loaded, "draft": self._draft_summary(effective_draft_id)}
        )

    async def save_world_draft(
        self, request: Any, draft_id: Optional[str] = None
    ) -> web.Response:
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

        effective_draft_id = self._request_draft_id(request, draft_id)
        try:
            save_result = self.world_builder.save_draft(effective_draft_id, world_data)
        except KeyError as error:
            return _error_response("draft_not_found", str(error), 404)
        except ValueError as error:
            return _error_response("invalid_draft", str(error), 400)
        return _json_response({"saved": save_result, "validation": validation})

    async def update_world_draft(
        self, request: Any, draft_id: Optional[str] = None
    ) -> web.Response:
        unauthorized = self._require_admin(request)
        if unauthorized is not None:
            return unauthorized

        payload = await self._read_json(request)
        if isinstance(payload, web.Response):
            return payload
        effective_draft_id = self._request_draft_id(request, draft_id)
        try:
            result = self.world_builder.rename_draft(
                effective_draft_id,
                name=payload.get("name"),
                description=payload.get("description"),
            )
        except KeyError as error:
            return _error_response("draft_not_found", str(error), 404)
        except ValueError as error:
            return _error_response("invalid_draft", str(error), 400)
        return _json_response(result)

    async def delete_world_draft(
        self, request: Any, draft_id: Optional[str] = None
    ) -> web.Response:
        unauthorized = self._require_admin(request)
        if unauthorized is not None:
            return unauthorized

        effective_draft_id = self._request_draft_id(request, draft_id)
        try:
            result = self.world_builder.delete_draft(effective_draft_id)
        except KeyError as error:
            return _error_response("draft_not_found", str(error), 404)
        except ValueError as error:
            return _error_response("invalid_draft", str(error), 400)
        return _json_response(result)

    async def activate_world_draft(
        self, request: Any, draft_id: Optional[str] = None
    ) -> web.Response:
        unauthorized = self._require_admin(request)
        if unauthorized is not None:
            return unauthorized

        effective_draft_id = self._request_draft_id(request, draft_id)
        try:
            result = self.world_builder.activate_draft(effective_draft_id)
        except KeyError as error:
            return _error_response("draft_not_found", str(error), 404)
        except ValueError as error:
            return _error_response("invalid_draft", str(error), 400)
        return _json_response(result)

    async def reset_world_draft(
        self, request: Any, draft_id: Optional[str] = None
    ) -> web.Response:
        unauthorized = self._require_admin(request)
        if unauthorized is not None:
            return unauthorized

        effective_draft_id = self._request_draft_id(request, draft_id)
        try:
            result = self.world_builder.reset_draft_from_baseline(
                effective_draft_id,
                self.world_factory,
            )
        except KeyError as error:
            return _error_response("draft_not_found", str(error), 404)
        except ValueError as error:
            return _error_response("invalid_draft", str(error), 400)

        payload = {
            "world": result["world"],
            "saved": result.get("saved", {}),
        }
        saved = payload["saved"]
        if isinstance(saved, dict):
            manifest = saved.get("manifest")
            if isinstance(manifest, dict):
                payload.update(manifest)
            draft = saved.get("draft")
            if isinstance(draft, dict):
                payload["draft"] = draft
        return _json_response(payload)

    async def apply_world_draft(
        self, request: Any, draft_id: Optional[str] = None
    ) -> web.Response:
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

        effective_draft_id = self._request_draft_id(request, draft_id)
        try:
            apply_validation = self._validation_to_dict(
                self.world_builder.apply_draft(effective_draft_id, world_data)
            )
        except KeyError as error:
            return _error_response("draft_not_found", str(error), 404)
        except ValueError as error:
            return _error_response("invalid_draft", str(error), 400)
        if not apply_validation.get("ok", False):
            return _json_response(
                {"error": "validation_failed", "validation": apply_validation},
                status=400,
            )
        return _json_response(
            {
                "saved": {"draft_id": effective_draft_id},
                "applied": self._apply_summary(world_data),
                "validation": validation,
            }
        )

    async def publish_world_draft(
        self, request: Any, draft_id: Optional[str] = None
    ) -> web.Response:
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

        effective_draft_id = self._request_draft_id(request, draft_id)
        try:
            publish_result = self.world_builder.publish_draft(
                effective_draft_id,
                world_data,
                checks=self._publish_checks(),
                message="Publish world data",
            )
        except KeyError as error:
            return _error_response("draft_not_found", str(error), 404)
        except ValueError as error:
            return _error_response("invalid_draft", str(error), 400)
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
                    "saved": {"draft_id": effective_draft_id},
                    "publish": publish_payload,
                    "validation": validation,
                },
                status=500,
            )
        return _json_response(
            {
                "saved": {"draft_id": effective_draft_id},
                "publish": publish_payload,
                "validation": validation,
            }
        )

    def _validation_to_dict(self, validation: Any) -> Dict[str, Any]:
        if hasattr(validation, "to_dict"):
            validation = validation.to_dict()
        return dict(validation)

    def _publish_to_dict(self, publish_result: Any) -> Dict[str, Any]:
        if hasattr(publish_result, "to_dict"):
            data: Dict[str, Any] = dict(publish_result.to_dict())
            data.setdefault("committed", bool(data.get("ok")))
            data.setdefault("pushed", bool(data.get("ok")))
            return data
        return dict(publish_result)

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

    def _request_draft_id(self, request: Any, draft_id: Optional[str] = None) -> str:
        if draft_id:
            return draft_id
        return str(getattr(request, "match_info", {}).get("draft_id") or "")

    def _draft_summary(self, draft_id: str) -> Dict[str, Any]:
        for draft in self.world_builder.list_drafts().get("drafts", []):
            if isinstance(draft, dict) and draft.get("id") == draft_id:
                return draft
        return {"id": draft_id}


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
            spawn_room_id=SPAWN_ROOM,
        )

    controller = AdminRouteController(
        game_state=game_state,
        mob_manager=mob_manager,
        online_sessions=online_sessions,
        world_builder=world_builder,
        world_factory=world_factory,
        publish_checks=publish_checks,
    )

    routes: Dict[str, Dict[str, Any]] = {
        "/admin/api/session": {
            "GET": controller.session,
        },
        "/admin/api/world": {
            "GET": controller.get_world,
            "POST": controller.save_world,
        },
        "/admin/api/world/mob-definitions": {
            "GET": controller.list_mob_definitions,
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
        "/admin/api/world/drafts": {
            "GET": controller.list_world_drafts,
            "POST": controller.create_world_draft,
        },
        "/admin/api/world/drafts/{draft_id}": {
            "GET": controller.get_world_draft,
            "POST": controller.save_world_draft,
            "PATCH": controller.update_world_draft,
            "DELETE": controller.delete_world_draft,
        },
        "/admin/api/world/drafts/{draft_id}/activate": {
            "POST": controller.activate_world_draft,
        },
        "/admin/api/world/drafts/{draft_id}/reset": {
            "POST": controller.reset_world_draft,
        },
        "/admin/api/world/drafts/{draft_id}/apply": {
            "POST": controller.apply_world_draft,
        },
        "/admin/api/world/drafts/{draft_id}/publish": {
            "POST": controller.publish_world_draft,
        },
    }

    for path, methods in routes.items():
        app.router.add_route("OPTIONS", path, controller.options)
        for method, handler in methods.items():
            app.router.add_route(method, path, handler)

    return controller
