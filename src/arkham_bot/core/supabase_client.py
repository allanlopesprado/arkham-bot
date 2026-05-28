import httpx

from .config import REQUEST_TIMEOUT_SECONDS, SUPABASE_ENABLED, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL


class SupabaseRestClient:
    def __init__(self, url: str, service_role_key: str):
        self.base_url = url.rstrip("/") + "/rest/v1"
        self.headers = {
            "apikey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        # Persistent HTTP client — reuses TCP+TLS connections across requests
        self._client = httpx.Client(
            timeout=REQUEST_TIMEOUT_SECONDS,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )

    def __del__(self):
        try:
            self._client.close()
        except Exception:
            pass

    def table_url(self, table: str) -> str:
        return f"{self.base_url}/{table}"

    def get(self, table: str, params: dict | None = None) -> list[dict]:
        response = self._client.get(self.table_url(table), headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def count(self, table: str, params: dict | None = None) -> int:
        """Returns exact row count using PostgREST count=exact header."""
        headers = dict(self.headers)
        headers["Prefer"] = "count=exact"
        all_params = {"select": "*", "limit": "1"}
        if params:
            all_params.update(params)
        response = self._client.get(self.table_url(table), headers=headers, params=all_params)
        response.raise_for_status()
        content_range = response.headers.get("content-range", "")
        if "/" in content_range:
            try:
                return int(content_range.split("/")[1])
            except (ValueError, IndexError):
                pass
        return len(response.json())

    def post(self, table: str, payload: dict | list[dict], prefer: str | None = None, params: dict | None = None) -> list[dict]:
        headers = dict(self.headers)
        if prefer:
            headers["Prefer"] = prefer
        response = self._client.post(self.table_url(table), headers=headers, params=params, json=payload)
        response.raise_for_status()
        return response.json() if response.content else []

    def upsert(self, table: str, payload: dict | list[dict], on_conflict: str | None = None, return_minimal: bool = True) -> list[dict]:
        prefer = "resolution=merge-duplicates"
        prefer += ",return=minimal" if return_minimal else ",return=representation"
        params = {"on_conflict": on_conflict} if on_conflict else None
        return self.post(table, payload, prefer=prefer, params=params)

    def patch(self, table: str, payload: dict, params: dict) -> list[dict]:
        response = self._client.patch(self.table_url(table), headers=self.headers, params=params, json=payload)
        response.raise_for_status()
        return response.json() if response.content else []

    def delete(self, table: str, params: dict) -> list[dict]:
        response = self._client.delete(self.table_url(table), headers=self.headers, params=params)
        response.raise_for_status()
        return response.json() if response.content else []


# Singleton client — one persistent connection pool for the whole process
_client_instance: SupabaseRestClient | None = None


def get_supabase_client() -> SupabaseRestClient | None:
    global _client_instance
    if not SUPABASE_ENABLED:
        return None
    if _client_instance is None:
        _client_instance = SupabaseRestClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    return _client_instance
