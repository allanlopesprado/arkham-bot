"""Future ArkhamDB OAuth helpers.

STUB/FUTURE PHASE: this module is intentionally not wired into the bot, Mini App,
or command worker. It must remain inactive until the ArkhamDB OAuth phase adds
secure token storage, callback validation, revocation, and admin-visible audit
logs. Tokens must never be sent to the Mini App frontend.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from .config import ARKHAMDB_OAUTH_CLIENT_ID, ARKHAMDB_OAUTH_CLIENT_SECRET, BASE_URL, REQUEST_TIMEOUT_SECONDS

AUTHORIZATION_ENDPOINT = BASE_URL.rstrip('/') + '/oauth/v2/auth'
TOKEN_ENDPOINT = BASE_URL.rstrip('/') + '/oauth/v2/token'


@dataclass(slots=True)
class ArkhamDBOAuthToken:
    access_token: str
    refresh_token: str | None = None
    expires_in: int | None = None
    token_type: str | None = None
    scope: str | None = None
    raw: dict | None = None


def generate_state() -> str:
    return secrets.token_urlsafe(32)


def build_authorization_url(redirect_uri: str, state: str, scope: str | None = None) -> str:
    if not ARKHAMDB_OAUTH_CLIENT_ID:
        raise RuntimeError('ARKHAMDB_OAUTH_CLIENT_ID is not configured')
    params = {
        'client_id': ARKHAMDB_OAUTH_CLIENT_ID,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'state': state,
    }
    if scope:
        params['scope'] = scope
    return f"{AUTHORIZATION_ENDPOINT}?{urlencode(params)}"


async def exchange_code_for_token(code: str, redirect_uri: str) -> ArkhamDBOAuthToken:
    if not ARKHAMDB_OAUTH_CLIENT_ID or not ARKHAMDB_OAUTH_CLIENT_SECRET:
        raise RuntimeError('ArkhamDB OAuth client credentials are not configured')
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
        response = await client.post(
            TOKEN_ENDPOINT,
            data={
                'grant_type': 'authorization_code',
                'client_id': ARKHAMDB_OAUTH_CLIENT_ID,
                'client_secret': ARKHAMDB_OAUTH_CLIENT_SECRET,
                'redirect_uri': redirect_uri,
                'code': code,
            },
        )
    response.raise_for_status()
    payload = response.json()
    return ArkhamDBOAuthToken(
        access_token=payload['access_token'],
        refresh_token=payload.get('refresh_token'),
        expires_in=payload.get('expires_in'),
        token_type=payload.get('token_type'),
        scope=payload.get('scope'),
        raw=payload,
    )


async def refresh_token(refresh_token: str) -> ArkhamDBOAuthToken:
    if not ARKHAMDB_OAUTH_CLIENT_ID or not ARKHAMDB_OAUTH_CLIENT_SECRET:
        raise RuntimeError('ArkhamDB OAuth client credentials are not configured')
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
        response = await client.post(
            TOKEN_ENDPOINT,
            data={
                'grant_type': 'refresh_token',
                'client_id': ARKHAMDB_OAUTH_CLIENT_ID,
                'client_secret': ARKHAMDB_OAUTH_CLIENT_SECRET,
                'refresh_token': refresh_token,
            },
        )
    response.raise_for_status()
    payload = response.json()
    return ArkhamDBOAuthToken(
        access_token=payload['access_token'],
        refresh_token=payload.get('refresh_token', refresh_token),
        expires_in=payload.get('expires_in'),
        token_type=payload.get('token_type'),
        scope=payload.get('scope'),
        raw=payload,
    )
