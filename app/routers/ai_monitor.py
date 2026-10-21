from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse


router = APIRouter(tags=["ai-monitor"])
from app.config import DATA_DIR

DATA_FILE = DATA_DIR / "ai_monitor.json"


def load_ai_monitor_data() -> dict[str, Any]:
    try:
        payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
    except (OSError, json.JSONDecodeError):
        pass
    return {"last_checked": "--", "models": [], "updates": []}


@router.get("/ai-monitor", response_class=HTMLResponse)
def page_ai_monitor(request: Request):
    ai_data = load_ai_monitor_data()
    models = ai_data.get("models") or []
    plans = ai_data.get("plans") or []
    model_groups: list[dict[str, Any]] = []
    model_groups_by_provider: dict[str, dict[str, Any]] = {}
    for model in models:
        provider = model.get("provider")
        if not provider:
            continue
        group = model_groups_by_provider.get(provider)
        if group is None:
            group = {
                "provider": provider,
                "provider_code": model.get("provider_code", ""),
                "models": [],
            }
            model_groups_by_provider[provider] = group
            model_groups.append(group)
        group["models"].append(model)

    plan_groups: list[dict[str, Any]] = []
    plan_groups_by_provider: dict[str, dict[str, Any]] = {}
    for plan in plans:
        provider = plan.get("provider")
        if not provider:
            continue
        group = plan_groups_by_provider.get(provider)
        if group is None:
            group = {
                "provider": provider,
                "provider_code": plan.get("provider_code", ""),
                "plans": [],
            }
            plan_groups_by_provider[provider] = group
            plan_groups.append(group)
        group["plans"].append(plan)

    stats = {
        "providers": len(model_groups),
        "models": len(models),
        "plans": len(plans),
        "price_changes": sum(
            1 for model in models if model.get("status") == "即将调价"
        ),
    }

    return request.app.state.templates.TemplateResponse(
        "ai_monitor.html",
        {
            "request": request,
            "active_page": "ai-monitor",
            "page_title": "AI监控",
            "ai_data": ai_data,
            "model_groups": model_groups,
            "plan_groups": plan_groups,
            "stats": stats,
        },
    )
