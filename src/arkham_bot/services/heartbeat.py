import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_INTERVAL_SECONDS = 60
_task: asyncio.Task | None = None


async def _beat(supabase_client):
    while True:
        try:
            await asyncio.sleep(_INTERVAL_SECONDS)
            now = datetime.now(timezone.utc).isoformat()
            # SupabaseRestClient.upsert is synchronous (httpx), run in executor
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: supabase_client.upsert(
                    'bot_settings',
                    {'key': 'last_heartbeat', 'value': f'"{now}"', 'description': 'Last Python bot heartbeat'},
                    on_conflict='key',
                ),
            )
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.debug('heartbeat error: %s', e)


async def start_heartbeat(supabase_client):
    global _task
    _task = asyncio.create_task(_beat(supabase_client))


async def stop_heartbeat(application=None):
    global _task
    if _task and not _task.done():
        _task.cancel()
        await asyncio.gather(_task, return_exceptions=True)
    _task = None
