import asyncio
import json
import logging
import datetime
import httpx
from sqlalchemy import select
from app.config import settings
from app.core.database import async_session_factory, init_db
from app.core.redis import get_redis_client
from app.core.clickhouse import get_telemetry_metrics
from app.models.alert import AlertRule, AlertHistory

logger = logging.getLogger("worker.alert")


class AlertEngineWorker:
    """
    Automated Real-Time Alert Engine.
    Continuously evaluates ClickHouse metrics against defined tenant rules
    and dispatches immediate HTTP webhook alerts on threshold violations.
    """

    def __init__(self):
        self.is_running = False

    async def start(self):
        self.is_running = True
        logger.info("Starting Automated Real-Time Alert Engine Worker...")
        await init_db()

        while self.is_running:
            try:
                await self.evaluate_all_rules()
                await asyncio.sleep(settings.ALERT_EVAL_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in Alert Engine evaluation loop: {e}")
                await asyncio.sleep(5.0)

        logger.info("Alert Engine Worker stopped.")

    async def evaluate_all_rules(self):
        """Fetches active rules and tests thresholds against ClickHouse."""
        async with async_session_factory() as session:
            stmt = select(AlertRule).where(AlertRule.is_active == True)
            result = await session.execute(stmt)
            active_rules = result.scalars().all()

            if not active_rules:
                return

            for rule in active_rules:
                try:
                    await self._evaluate_rule(rule, session)
                except Exception as re:
                    logger.error(f"Error evaluating rule '{rule.id}' ({rule.name}): {re}")

    async def _evaluate_rule(self, rule: AlertRule, session):
        # 1. Query ClickHouse metrics for the rule's time window
        window_seconds = rule.window_minutes * 60
        metrics = get_telemetry_metrics(
            tenant_id=rule.tenant_id,
            time_window_seconds=window_seconds,
        )

        total_requests = metrics.get("total_requests", 0)
        if total_requests == 0:
            return  # No traffic in window

        current_val = 0.0
        triggered = False

        if rule.metric_type == "p95_latency":
            current_val = float(metrics.get("latency_percentiles_ms", {}).get("p95", 0.0))
            if current_val > rule.threshold:
                triggered = True
        elif rule.metric_type == "error_rate":
            current_val = float(metrics.get("error_rate_pct", 0.0))
            if current_val > rule.threshold:
                triggered = True
        elif rule.metric_type == "req_count":
            current_val = float(total_requests)
            if current_val > rule.threshold:
                triggered = True

        if not triggered:
            return

        # 2. Check Cooldown in Redis (Avoid webhook spamming)
        r = await get_redis_client()
        cooldown_key = f"alert_cooldown:{rule.id}"
        is_in_cooldown = await r.get(cooldown_key)
        if is_in_cooldown:
            return

        # Set 5 minute cooldown
        await r.set(cooldown_key, "active", ex=300)

        # 3. Dispatch Webhook Alert to external endpoint
        payload = {
            "event": "alert.triggered",
            "rule_id": rule.id,
            "tenant_id": rule.tenant_id,
            "rule_name": rule.name,
            "metric_type": rule.metric_type,
            "current_value": current_val,
            "threshold": rule.threshold,
            "window_minutes": rule.window_minutes,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "severity": "critical",
        }

        dispatch_status = "sent"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(rule.webhook_url, json=payload)
                if resp.status_code >= 400:
                    dispatch_status = f"failed_http_{resp.status_code}"
        except Exception as we:
            dispatch_status = f"failed_{str(we)[:30]}"
            logger.error(f"Webhook dispatch failed to {rule.webhook_url}: {we}")

        # 4. Record in AlertHistory
        history_entry = AlertHistory(
            rule_id=rule.id,
            tenant_id=rule.tenant_id,
            metric_type=rule.metric_type,
            triggered_value=current_val,
            threshold=rule.threshold,
            status=dispatch_status,
            payload=json.dumps(payload),
        )
        session.add(history_entry)
        await session.commit()

        logger.warning(
            f"ALERT TRIGGERED for tenant '{rule.tenant_id}': Rule '{rule.name}' ({rule.metric_type} = {current_val} > {rule.threshold}). Dispatched to {rule.webhook_url}"
        )

    def stop(self):
        self.is_running = False


alert_worker = AlertEngineWorker()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(alert_worker.start())
    except KeyboardInterrupt:
        alert_worker.stop()
