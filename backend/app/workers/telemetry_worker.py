import asyncio
import logging
import time
from typing import List, Dict, Any
from app.config import settings
from app.core.redis import get_redis_client
from app.core.clickhouse import insert_telemetry_batch

logger = logging.getLogger("worker.telemetry")


class TelemetryWorker:
    """
    Decoupled high-throughput background daemon worker.
    Consumes stream batches from Redis Streams and bulk-inserts into ClickHouse.
    """

    def __init__(self):
        self.is_running = False
        self._task = None

    async def start(self):
        self.is_running = True
        logger.info(f"Starting Telemetry Stream Ingestion Worker for '{settings.REDIS_STREAM_KEY}'...")
        r = await get_redis_client()

        # Initialize consumer group if needed
        try:
            await r.xgroup_create(
                settings.REDIS_STREAM_KEY,
                settings.REDIS_STREAM_GROUP,
                id="0",
                mkstream=True,
            )
            logger.info(f"Created consumer group '{settings.REDIS_STREAM_GROUP}'")
        except Exception:
            # Group already exists
            pass

        consumer_name = f"worker_{int(time.time())}"

        while self.is_running:
            try:
                # Read batch of messages from stream
                # Try consumer group read first, fallback to basic xread if needed
                messages = []
                try:
                    entries = await r.xreadgroup(
                        groupname=settings.REDIS_STREAM_GROUP,
                        consumername=consumer_name,
                        streams={settings.REDIS_STREAM_KEY: ">"},
                        count=settings.TELEMETRY_BATCH_SIZE,
                        block=settings.TELEMETRY_FLUSH_INTERVAL_MS,
                    )
                    if entries:
                        for stream_name, stream_msgs in entries:
                            messages.extend(stream_msgs)
                except Exception:
                    # Fallback to basic XREAD
                    entries = await r.xread(
                        streams={settings.REDIS_STREAM_KEY: "0-0"},
                        count=settings.TELEMETRY_BATCH_SIZE,
                        block=settings.TELEMETRY_FLUSH_INTERVAL_MS,
                    )
                    if entries:
                        for stream_name, stream_msgs in entries:
                            messages.extend(stream_msgs)

                if messages:
                    batch_rows: List[Dict[str, Any]] = []
                    msg_ids = []

                    for msg_id, payload in messages:
                        msg_ids.append(msg_id)
                        batch_rows.append(payload)

                    # Flush batch to ClickHouse OLAP
                    success = await insert_telemetry_batch(batch_rows)
                    if success:
                        try:
                            # Acknowledge processed messages
                            await r.xack(
                                settings.REDIS_STREAM_KEY,
                                settings.REDIS_STREAM_GROUP,
                                *msg_ids,
                            )
                            # Trim stream to keep memory low
                            await r.xdel(settings.REDIS_STREAM_KEY, *msg_ids)
                        except Exception:
                            pass
                        logger.debug(f"Flushed batch of {len(batch_rows)} logs into ClickHouse")

                await asyncio.sleep(0.05)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in telemetry worker loop: {e}")
                await asyncio.sleep(1.0)

        logger.info("Telemetry Stream Ingestion Worker stopped.")

    def stop(self):
        self.is_running = False


telemetry_worker = TelemetryWorker()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(telemetry_worker.start())
    except KeyboardInterrupt:
        telemetry_worker.stop()
