"""
JWT authentication middleware for Django Channels WebSocket connections.

Reads `?token=<access_jwt>` from the WebSocket URL query string and sets
`scope["user"]` so consumers can rely on standard auth checks.
"""
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()


@database_sync_to_async
def _get_user(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()


class JwtAuthMiddleware:
    """
    ASGI middleware that authenticates WebSocket connections via a JWT
    access token passed as the `token` query-string parameter.

    Usage in asgi.py:
        application = ProtocolTypeRouter({
            "websocket": JwtAuthMiddleware(
                URLRouter([...])
            ),
        })
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":
            qs = parse_qs(scope.get("query_string", b"").decode())
            token_list = qs.get("token", [])
            token_str = token_list[0] if token_list else None

            if token_str:
                try:
                    token = AccessToken(token_str)
                    user_id = token["user_id"]
                    scope["user"] = await _get_user(user_id)
                except (InvalidToken, TokenError, KeyError):
                    scope["user"] = AnonymousUser()
            else:
                scope["user"] = AnonymousUser()

        return await self.app(scope, receive, send)
