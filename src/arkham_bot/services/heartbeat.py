import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_INTERVAL_SECONDS = 60
_task: asyncio.Task | None = None


async def _write_heartbeat(supabase_client):
    now = datetime.now(timezone.utc).isoformat()
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: supabase_client.upsert(
            'bot_settings',
            {'key': 'last_heartbeat', 'value': f'"{now}"', 'description': 'Last Python bot heartbeat'},
            on_conflict='key',
        ),
    )


async def _beat(supabase_client):
    while True:
        try:
            await _write_heartbeat(supabase_client)
            await asyncio.sleep(_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.debug('heartbeat error: %s', e)
            await asyncio.sleep(_INTERVAL_SECONDS)


async def start_heartbeat(supabase_client):
    global _task
    if _task and not _task.done():
        return
    _task = asyncio.create_task(_beat(supabase_client))


async def stop_heartbeat(application=None):
    global _task
    if _task and not _task.done():
        _task.cancel()
        await asyncio.gather(_task, return_exceptions=True)
    _task = None
