from __future__ import annotations

import csv
import json
import os
import re
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import select

from .models import DailyBriefing, DailyReport
from .utils import safe_float

def normalize_date_str(date_str: str) -> str:
    # Converts "2026.6.15" or "2026.06.15" to "2026-06-15"
    parts = date_str.split('.')
    if len(parts) == 3:
        try:
            return f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"
        except ValueError:
            return date_str
    return date_str

def get_briefing_dir() -> Path:
    configured = os.getenv("BRIEFING_DIR", "").strip()
    if configured:
        return Path(configured).expanduser()

    project_root = Path(__file__).resolve().parents[1]
    sibling = project_root.parent / "每日简报"
    if sibling.exists() and sibling.is_dir():
        return sibling

    # Compatibility fallback for a conventional Desktop checkout.
    user_home = Path.home()
    p_desktop = user_home / "Desktop" / "每日简报"
    if p_desktop.exists() and p_desktop.is_dir():
        return p_desktop
    return sibling

def import_daily_briefings(db: Session, csv_path: Path) -> int:
    if not csv_path.exists():
        return 0
        
    count = 0
    try:
        existing_map = {
            (b.date, b.ticker): b
            for b in db.execute(select(DailyBriefing)).scalars().all()
        }
        
        with open(csv_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            required = {"date", "ticker", "action", "price", "buyRange", "changeReason", "sourceFile"}
            if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
                print(f"CSV missing columns. Found: {reader.fieldnames}")
                return 0
                
            for row in reader:
                ticker = row["ticker"].strip().upper()
                raw_date = row["date"].strip()
                date = normalize_date_str(raw_date)
                price = safe_float(row["price"])
                
                existing = existing_map.get((date, ticker))
                if existing:
                    existing.action = row["action"].strip()
                    existing.price = price
                    existing.buy_range = row["buyRange"].strip()
                    existing.change_reason = row["changeReason"].strip()
                    existing.source_file = row["sourceFile"].strip()
                    db.add(existing)
                else:
                    briefing = DailyBriefing(
                        date=date,
                        ticker=ticker,
                        action=row["action"].strip(),
                        price=price,
                        buy_range=row["buyRange"].strip(),
                        change_reason=row["changeReason"].strip(),
                        source_file=row["sourceFile"].strip()
                    )
                    db.add(briefing)
                    existing_map[(date, ticker)] = briefing
                    count += 1
            db.commit()
    except Exception as e:
        print(f"Error importing briefings: {e}")
    return count

def import_daily_reports(db: Session, folder: Path) -> int:
    count = 0
    if not folder.exists() or not folder.is_dir():
        return 0

    try:
        existing_map = {
            (r.title, r.file_type): r
            for r in db.execute(select(DailyReport)).scalars().all()
        }
        
        for file_path in folder.rglob("*"):
            if not file_path.is_file():
                continue
            filename = file_path.name
            if not filename.startswith("每日简报-"):
                continue
            
            ext = filename.split('.')[-1].lower()
            if ext not in ("txt", "html"):
                continue
                
            date_match = re.search(r'20\d{2}\.\d{1,2}\.\d{1,2}', filename)
            if not date_match:
                continue
                
            raw_date = date_match.group(0)
            date = normalize_date_str(raw_date)
            title = filename.rsplit('.', 1)[0]
            
            category = "其他"
            if "总览" in filename:
                category = "总览"
            elif "AI" in filename:
                category = "AI"
            elif "传统行业" in filename:
                category = "传统行业"
                
            content = ""
            for encoding in ("utf-8", "gbk", "utf-8-sig"):
                try:
                    content = file_path.read_text(encoding=encoding)
                    break
                except Exception:
                    continue
                    
            if not content:
                continue
                
            existing = existing_map.get((title, ext))
            if existing:
                existing.content = content
                existing.date = date
                existing.category = category
                db.add(existing)
            else:
                report = DailyReport(
                    date=date,
                    category=category,
                    file_type=ext,
                    title=title,
                    content=content
                )
                db.add(report)
                existing_map[(title, ext)] = report
                count += 1
        db.commit()
    except Exception as e:
        print(f"Error importing reports: {e}")
    return count

def run_import(db: Session) -> dict[str, int]:
    folder = get_briefing_dir()
    results = {"briefings": 0, "reports": 0}
    if folder.exists() and folder.is_dir():
        csv_path = folder / "00_核心数据" / "股票评估历史.csv"
        if not csv_path.exists():
            # Compatibility fallback: never read archived/backed-up history as current data.
            found_paths = [
                path for path in folder.rglob("股票评估历史.csv")
                if "06_备份归档" not in path.parts
            ]
            if found_paths:
                csv_path = found_paths[0]
        report_folder = folder / "01_简报正文"
        if not report_folder.exists():
            report_folder = folder
        results["briefings"] = import_daily_briefings(db, csv_path)
        results["reports"] = import_daily_reports(db, report_folder)
    return results
