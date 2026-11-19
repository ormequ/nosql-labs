"""Rates API capped by a Redis sliding-window rate limiter"""
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
    multiprocess,
)
from redis import Redis
from redis.exceptions import RedisError

RATES = {"USD/RUB": 81.93, "EUR/RUB": 89.86, "CNY/RUB": 12.25}


def env_map(name: str) -> dict[str, str]:
    return dict(p.split("=") for p in os.environ[name].split(",") if p)


LIMITS = {tier: int(v) for tier, v in env_map("APP_LIMITS").items()}
KEY_TIERS = env_map("APP_KEY_TIERS")
# unknown keys fall back to free, so free needs a limit too
assert set(KEY_TIERS.values()) | {"free"} <= LIMITS.keys(), "a tier has no limit in APP_LIMITS"
WINDOW = int(os.environ["APP_WINDOW"])

redis_client = Redis(
    host=os.environ["APP_REDIS_HOST"],
    port=int(os.environ["APP_REDIS_PORT"]),
    password=os.environ["APP_REDIS_PASSWORD"],
)
ratelimit = redis_client.register_script(Path(os.environ["APP_LUA_SCRIPT"]).read_text(encoding="utf-8"))

app = FastAPI(title="Rates API")

REQUESTS = Counter("api_requests_total", "Total API requests", ["status", "tier"])
LATENCY = Histogram(
    "api_request_latency_seconds", "Request latency",
    ["tier"], buckets=(0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5),
)
LIMITER_LATENCY = Histogram(
    "api_limiter_latency_seconds", "Rate limiter Lua call latency",
    buckets=(0.0001, 0.00025, 0.0005, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05),
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/rates")
def rates(request: Request, response: Response) -> dict:
    key = request.headers.get("X-API-KEY")
    # the server decides the tier from the key, the client cannot pick a higher limit
    tier = KEY_TIERS.get(key, "free")
    # time the whole handler, not the return: the panel shows the full request budget
    with LATENCY.labels(tier=tier).time():
        if not key:
            REQUESTS.labels(status="401", tier=tier).inc()
            raise HTTPException(status_code=401, detail="X-API-KEY header required")
        try:
            with LIMITER_LATENCY.time():
                allowed, retry_after, remaining = ratelimit(
                    keys=[f"ratelimit:{tier}:{key}"], args=[LIMITS[tier], WINDOW]
                )
        except RedisError as exc:
            # fail-closed: with Redis unavailable answer 503, never serve unlimited
            REQUESTS.labels(status="503", tier=tier).inc()
            raise HTTPException(status_code=503, detail="rate limiter unavailable") from exc
        REQUESTS.labels(status="200" if allowed else "429", tier=tier).inc()
        if not allowed:
            # HTTPException builds its own Response, so headers go to its constructor
            raise HTTPException(
                status_code=429,
                detail="rate limit exceeded",
                headers={"Retry-After": str(retry_after), "X-RateLimit-Remaining": str(remaining)},
            )
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return {"rates": RATES}


@app.get("/metrics")
def metrics() -> Response:
    # a second uvicorn worker means per-process counters, merged on each scrape
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)
    return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)
