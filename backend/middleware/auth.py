from functools import wraps
from flask import request, g, jsonify
from config.settings import settings
from config.logging_config import logger

from clerk_backend_api import Clerk
from clerk_backend_api.security import authenticate_request
from clerk_backend_api.security.types import AuthenticateRequestOptions
import httpx

clerk_client = None


def initialize_clerk():
    """
    Lazily initialize a singleton Clerk client using the secret key.
    """
    global clerk_client
    if clerk_client:
        return clerk_client

    try:
        if not settings.CLERK_SECRET_KEY:
            logger.warning("⚠️ CLERK_SECRET_KEY not configured")
            return None

        clerk_client = Clerk(bearer_auth=settings.CLERK_SECRET_KEY)
        logger.info("✅ Clerk authentication initialized")
        return clerk_client
    except Exception as e:
        logger.error(f"❌ Clerk initialization failed: {e}")
        return None


def get_token_from_request():
    """
    Extract Bearer token from Authorization header or X-Auth-Token.
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header:
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
    return request.headers.get("X-Auth-Token")


def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            token = get_token_from_request()
            if not token:
                return jsonify({"success": False, "message": "No authentication token provided"}), 401

            client = initialize_clerk()
            if not client:
                return jsonify({"success": False, "message": "Authentication service unavailable"}), 503

            try:
                # Build a minimal httpx.Request
                req = httpx.Request(
                    "GET",
                    "http://localhost",
                    headers={"Authorization": f"Bearer {token}"},
                )

                # Create options object
                options = AuthenticateRequestOptions(
                    secret_key=settings.CLERK_SECRET_KEY,
                )

                # Pass request and options
                request_state = authenticate_request(req, options)

                # Add logging
                logger.info(f"Token: {token}")
                logger.info(f"Session claims: {request_state.session_claims}")

                if not request_state.is_signed_in:
                    raise ValueError(request_state.error_reason or "Not signed in")

                # Prefer user_id directly
                user_id = request_state.user_id
                if not user_id:
                    raise ValueError("Token missing user_id")

                user = client.users.get(user_id)

                g.user_id = user.id
                g.user_email = (
                    user.email_addresses[0].email_address
                    if getattr(user, "email_addresses", [])
                    else None
                )
                g.user_name = f"{user.first_name or ''} {user.last_name or ''}".strip()

            except Exception as e:
                logger.error(f"Token verification failed: {e}")
                return jsonify({"success": False, "message": "Invalid or expired authentication token"}), 401

            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Auth error: {e}")
            return jsonify({"success": False, "message": "Authentication error"}), 500

    return decorated_function