from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any


DEFAULT_DATA_FILE = Path(__file__).resolve().parents[4] / "data" / "ai_monitor.json"
MODEL_FIELDS = {
    "provider", "provider_code", "model", "positioning", "currency", "currency_symbol",
    "input_price", "cached_input_price", "output_price", "context", "status", "status_tone",
    "pricing_note", "source_label", "source_url",
}
PLAN_FIELDS = {"provider", "provider_code", "plan", "price", "currency_symbol", "billing", "note", "source_url"}
UPDATE_FIELDS = {"date", "provider", "tag", "title"}
ALLOWED_TONES = {"stable", "promo", "warning", "new", "opensource"}


def is_price(value: Any, *, nullable: bool = True) -> bool:
    if value is None:
        return nullable
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0


def validate(payload: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["根节点必须是JSON对象"]

    try:
        date.fromisoformat(payload.get("last_checked", ""))
    except (TypeError, ValueError):
        errors.append("last_checked必须是YYYY-MM-DD")

    models = payload.get("models")
    plans = payload.get("plans")
    updates = payload.get("updates")
    if not isinstance(models, list):
        errors.append("models必须是数组")
        models = []
    if not isinstance(plans, list):
        errors.append("plans必须是数组")
        plans = []
    if not isinstance(updates, list):
        errors.append("updates必须是数组")
        updates = []

    seen_models: set[tuple[str, str]] = set()
    closed_model_providers: set[str] = set()
    last_model_provider: str | None = None
    for index, model in enumerate(models):
        prefix = f"models[{index}]"
        if not isinstance(model, dict):
            errors.append(f"{prefix}必须是对象")
            continue
        missing = MODEL_FIELDS - model.keys()
        if missing:
            errors.append(f"{prefix}缺少字段: {', '.join(sorted(missing))}")
        key = (str(model.get("provider", "")), str(model.get("model", "")))
        provider = key[0]
        if provider != last_model_provider:
            if provider in closed_model_providers:
                errors.append(f"{prefix}的厂商{provider}未连续排列")
            if last_model_provider is not None:
                closed_model_providers.add(last_model_provider)
            last_model_provider = provider
        if key in seen_models:
            errors.append(f"{prefix}重复模型: {key[0]} / {key[1]}")
        seen_models.add(key)
        for field in ("input_price", "cached_input_price", "output_price"):
            if not is_price(model.get(field)):
                errors.append(f"{prefix}.{field}必须是非负数字或null")
        if model.get("status_tone") not in ALLOWED_TONES:
            errors.append(f"{prefix}.status_tone不受支持")
        if model.get("input_price") is not None and not model.get("currency_symbol"):
            errors.append(f"{prefix}有价格时必须填写currency_symbol")
        if not str(model.get("source_url", "")).startswith("https://"):
            errors.append(f"{prefix}.source_url必须是HTTPS官方链接")

    seen_plans: set[tuple[str, str]] = set()
    for index, plan in enumerate(plans):
        prefix = f"plans[{index}]"
        if not isinstance(plan, dict):
            errors.append(f"{prefix}必须是对象")
            continue
        missing = PLAN_FIELDS - plan.keys()
        if missing:
            errors.append(f"{prefix}缺少字段: {', '.join(sorted(missing))}")
        key = (str(plan.get("provider", "")), str(plan.get("plan", "")))
        if key in seen_plans:
            errors.append(f"{prefix}重复套餐: {key[0]} / {key[1]}")
        seen_plans.add(key)
        if not is_price(plan.get("price")):
            errors.append(f"{prefix}.price必须是非负数字或null")
        if plan.get("price") is not None and plan.get("price") > 0 and not plan.get("currency_symbol"):
            errors.append(f"{prefix}有固定价格时必须填写currency_symbol")
        if plan.get("price") is None and plan.get("billing") not in {"地区定价", "联系销售", "按量计费", "自托管"}:
            errors.append(f"{prefix}.price为null时billing口径不受支持")
        if not str(plan.get("source_url", "")).startswith("https://"):
            errors.append(f"{prefix}.source_url必须是HTTPS官方链接")

    for index, update in enumerate(updates):
        prefix = f"updates[{index}]"
        if not isinstance(update, dict):
            errors.append(f"{prefix}必须是对象")
            continue
        missing = UPDATE_FIELDS - update.keys()
        if missing:
            errors.append(f"{prefix}缺少字段: {', '.join(sorted(missing))}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="校验FinBoard AI监控数据")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA_FILE, help="ai_monitor.json路径")
    args = parser.parse_args()
    try:
        payload = json.loads(args.data.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: 无法读取{args.data}: {exc}", file=sys.stderr)
        return 1
    errors = validate(payload)
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(f"OK: {len(payload['models'])}个模型，{len(payload['plans'])}个套餐，核对日期{payload['last_checked']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
