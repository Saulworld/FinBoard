from datetime import date
from calendar import monthrange
import re
from app.utils import load_wallet_card_records, load_phone_records, calculate_phone_status

def card_expiry_status(expiry, today=None):
    today = today or date.today()
    m = re.fullmatch(r"(0[1-9]|1[0-2])/(\d{2}|\d{4})", str(expiry or ""))
    if not m: return None
    month, year = int(m[1]), int(m[2])
    if len(m[2]) == 2: year += 2000
    end = date(year, month, monthrange(year, month)[1])
    index = year * 12 + month - 1 - 3
    sy, sm = divmod(index, 12); sm += 1
    start = date(sy, sm, min(end.day, monthrange(sy, sm)[1]))
    if today < start: return None
    days = (end-today).days
    return {"status": "expired" if days < 0 else "expiring_soon", "days_remaining": days,
            "expiry_date": end.isoformat(), "label": "已过期" if days < 0 else "今日到期" if days == 0 else f"剩余{days}天"}

def wallet_alerts():
    result=[]
    for card in load_wallet_card_records():
        state=card_expiry_status(card.get("expiry"))
        if state:
            result.append({"id":card["id"],"name":card.get("name", ""), "phone":"•••• "+str(card.get("card_number", ""))[-4:], "country":"", **state})
    return sorted(result,key=lambda r:r["days_remaining"])

def phone_alerts():
    result=[]
    for phone in load_phone_records():
        if str(phone.get("status") or "").strip() in {"关闭","已关闭"}: continue
        state=calculate_phone_status(phone.get("expiry_date"))
        if state["status"] in {"expired","expiring_soon"}:
            days=state["days_remaining"]
            result.append({**phone,**state,"label":"已过期" if days<0 else "今日到期" if days==0 else f"剩余{days}天"})
    return sorted(result,key=lambda r:r["days_remaining"])
