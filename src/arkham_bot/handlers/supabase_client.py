"""Compatibility wrapper for legacy handler-local imports.

Runtime handlers should use ``arkham_bot.core.supabase_client`` directly.
This module exists to keep older relative imports working while the
handler module is consolidated.
"""

from ..core.supabase_client import SupabaseRestClient, get_supabase_client

__all__ = ["SupabaseRestClient", "get_supabase_client"]
