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

    def table_url(self, table: str) -> str:
        return f"{self.base_url}/{table}"

    def get(self, table: str, params: dict | None = None) -> list[dict]:
        response = httpx.get(self.table_url(table), headers=self.headers, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()

    def count(self, table: str, params: dict | None = None) -> int:
        """Returns exact row count using PostgREST count=exact header."""
        headers = dict(self.headers)
        headers["Prefer"] = "count=exact"
        all_params = {"select": "*", "limit": "1"}
        if params:
            all_params.update(params)
        response = httpx.get(self.table_url(table), headers=headers, params=all_params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        content_range = response.headers.get("content-range", "")
        # PostgREST returns Content-Range: 0-0/TOTAL
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
        response = httpx.post(self.table_url(table), headers=headers, params=params, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json() if response.content else []

    def upsert(self, table: str, payload: dict | list[dict], on_conflict: str | None = None, return_minimal: bool = True) -> list[dict]:
        prefer = "resolution=merge-duplicates"
        prefer += ",return=minimal" if return_minimal else ",return=representation"
        params = {"on_conflict": on_conflict} if on_conflict else None
        return self.post(table, payload, prefer=prefer, params=params)

    def patch(self, table: str, payload: dict, params: dict) -> list[dict]:
        response = httpx.patch(self.table_url(table), headers=self.headers, params=params, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json() if response.content else []

    def delete(self, table: str, params: dict) -> list[dict]:
        response = httpx.delete(self.table_url(table), headers=self.headers, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json() if response.content else []


def get_supabase_client():
    if not SUPABASE_ENABLED:
        return None
    return SupabaseRestClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
