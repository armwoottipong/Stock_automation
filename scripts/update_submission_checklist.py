"""Generate and update the stock submission checklist HTML and JSON.

This script scans output/ sets, compiles project records, generates a standalone
HTML checklist with localStorage persistence, and optionally deploys/pushes to GitHub Pages.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "output"
DEFAULT_DOCS = ROOT / "docs"


def scan_output_sets(output_dir: Path) -> list[dict[str, Any]]:
    """Scan finalized output directories and return structured project data."""
    if not output_dir.is_dir():
        return []

    projects: list[dict[str, Any]] = []

    for entry in sorted(output_dir.iterdir(), reverse=True):
        if not entry.is_dir() or entry.name.startswith("."):
            continue

        set_id = entry.name

        # Extract date from set_id or folder modification time
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", set_id)
        if date_match:
            date_str = date_match.group(1)
        else:
            try:
                import datetime
                mtime = entry.stat().st_mtime
                date_str = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
            except Exception:
                date_str = "Unknown"

        # Read set_manifest.json
        packages: list[str] = []
        sm_path = entry / "set_manifest.json"
        if sm_path.is_file():
            try:
                sm_data = json.loads(sm_path.read_text(encoding="utf-8"))
                packages = sm_data.get("packages", [])
            except Exception:
                pass

        # Image count & description / sample title
        image_count = 0
        title = ""
        keywords_sample: list[str] = []

        # Check metadata catalog first
        cat_file = entry / "metadata" / "catalog.json"
        if not cat_file.is_file():
            cat_file = entry / "adobe_stock" / "catalog.json"

        if cat_file.is_file():
            try:
                cat_data = json.loads(cat_file.read_text(encoding="utf-8"))
                records = cat_data.get("records", []) if isinstance(cat_data, dict) else cat_data
                if isinstance(records, list) and records:
                    image_count = len(records)
                    first_record = records[0]
                    if isinstance(first_record, dict):
                        title = first_record.get("title", "")
                        keywords_sample = first_record.get("keywords", [])[:5]
            except Exception:
                pass

        # Check adobe_stock.csv if title or count still missing
        csv_file = entry / "metadata" / "adobe_stock.csv"
        if not csv_file.is_file():
            csv_file = entry / "adobe_stock" / "adobe_stock.csv"

        if csv_file.is_file():
            try:
                with csv_file.open("r", encoding="utf-8", errors="ignore") as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    if not image_count and rows:
                        image_count = len(rows)
                    if not title and rows:
                        title = rows[0].get("Title", "")
            except Exception:
                pass

        # Check submission_manifest.json if count still missing
        if image_count == 0:
            for sub_name in [
                entry / "metadata" / "submission_manifest.json",
                entry / "adobe_stock" / "submission_manifest.json",
            ]:
                if sub_name.is_file():
                    try:
                        sub_data = json.loads(sub_name.read_text(encoding="utf-8"))
                        image_count = sub_data.get("image_count", 0)
                        if image_count:
                            break
                    except Exception:
                        pass

        # Fallback to counting images in adobe_stock or any package
        if image_count == 0:
            as_dir = entry / "adobe_stock"
            if as_dir.is_dir():
                image_count = len([f for f in as_dir.iterdir() if f.suffix.lower() in (".png", ".jpg", ".jpeg")])

        if not title:
            # Clean human title from set_id
            clean_name = re.sub(r"_\d{4}-\d{2}-\d{2}(_\d+)?", "", set_id)
            title = clean_name.replace("_", " ").title()

        has_csv = (entry / "metadata" / "adobe_stock.csv").is_file() or (entry / "adobe_stock" / "adobe_stock.csv").is_file()
        has_white_jpg = (entry / "white_jpeg_companion").is_dir()
        has_transparent_png = (entry / "adobe_stock").is_dir()
        has_contact_sheet = (entry / "metadata" / "contact_sheet_4k.jpg").is_file()

        projects.append({
            "id": set_id,
            "date": date_str,
            "title": title,
            "image_count": image_count,
            "packages": packages,
            "has_csv": has_csv,
            "has_white_jpg": has_white_jpg,
            "has_transparent_png": has_transparent_png,
            "has_contact_sheet": has_contact_sheet,
            "keywords_sample": keywords_sample,
        })

    return projects


def build_checklist_html(projects: list[dict[str, Any]]) -> str:
    """Generate the interactive HTML submission checklist with localStorage persistence."""
    projects_json = json.dumps(projects, ensure_ascii=False, indent=2)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Stock Submission Checklist | Automation Hub</title>
  <style>
    :root {{
      --bg-primary: #0b0f19;
      --bg-secondary: #131d31;
      --bg-card: #1c273e;
      --bg-card-hover: #23314e;
      --border-color: #2e3e60;
      --border-focus: #3b82f6;
      --text-main: #f1f5f9;
      --text-muted: #94a3b8;
      --text-dim: #64748b;
      --accent-blue: #3b82f6;
      --accent-indigo: #6366f1;
      --accent-emerald: #10b981;
      --accent-amber: #f59e0b;
      --accent-rose: #f43f5e;
      --accent-cyan: #06b6d4;
      --badge-bg: rgba(59, 130, 246, 0.12);
      --badge-text: #60a5fa;
      --success-bg: rgba(16, 185, 129, 0.15);
      --success-text: #34d399;
      --warning-bg: rgba(245, 158, 11, 0.15);
      --warning-text: #fbbf24;
      --radius: 12px;
      --radius-sm: 8px;
      --shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4), 0 8px 10px -6px rgba(0, 0, 0, 0.3);
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }}

    body {{
      background: var(--bg-primary);
      color: var(--text-main);
      min-height: 100vh;
      padding: 24px;
      line-height: 1.5;
    }}

    .container {{
      max-width: 1400px;
      margin: 0 auto;
    }}

    /* Header */
    header {{
      background: linear-gradient(135deg, #131d31 0%, #17243e 100%);
      border: 1px solid var(--border-color);
      border-radius: var(--radius);
      padding: 28px;
      margin-bottom: 24px;
      box-shadow: var(--shadow);
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 20px;
    }}

    .header-title-group h1 {{
      font-size: 26px;
      font-weight: 800;
      letter-spacing: -0.5px;
      display: flex;
      align-items: center;
      gap: 12px;
      background: linear-gradient(to right, #60a5fa, #34d399);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }}

    .header-title-group p {{
      color: var(--text-muted);
      font-size: 14px;
      margin-top: 6px;
    }}

    .header-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }}

    .btn {{
      background: var(--bg-card);
      color: var(--text-main);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      padding: 8px 16px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s ease;
      text-decoration: none;
    }}

    .btn:hover {{
      background: var(--bg-card-hover);
      border-color: var(--border-focus);
      transform: translateY(-1px);
    }}

    .btn-primary {{
      background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
      border-color: #3b82f6;
      color: #fff;
    }}

    .btn-primary:hover {{
      background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
    }}

    .btn-success {{
      background: linear-gradient(135deg, #059669 0%, #047857 100%);
      border-color: #10b981;
      color: #fff;
    }}

    .btn-sm {{
      padding: 4px 10px;
      font-size: 12px;
      border-radius: 6px;
    }}

    /* Metrics Bar */
    .metrics-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }}

    .metric-card {{
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: var(--radius);
      padding: 18px 20px;
      position: relative;
      overflow: hidden;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }}

    .metric-card::before {{
      content: "";
      position: absolute;
      top: 0;
      left: 0;
      width: 4px;
      height: 100%;
      background: var(--accent-blue);
    }}

    .metric-card.adobe::before {{ background: #ff0000; }}
    .metric-card.shutter::before {{ background: #f59e0b; }}
    .metric-card.rf123::before {{ background: #06b6d4; }}
    .metric-card.others::before {{ background: #8b5cf6; }}
    .metric-card.total::before {{ background: #10b981; }}

    .metric-label {{
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-muted);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    .metric-value {{
      font-size: 26px;
      font-weight: 800;
      color: var(--text-main);
      margin-top: 6px;
      display: flex;
      align-items: baseline;
      gap: 6px;
    }}

    .metric-sub {{
      font-size: 12px;
      font-weight: 500;
      color: var(--text-dim);
    }}

    .metric-bar-bg {{
      width: 100%;
      height: 6px;
      background: rgba(255, 255, 255, 0.08);
      border-radius: 999px;
      margin-top: 10px;
      overflow: hidden;
    }}

    .metric-bar-fill {{
      height: 100%;
      background: var(--accent-blue);
      border-radius: 999px;
      transition: width 0.4s ease;
    }}

    .metric-card.adobe .metric-bar-fill {{ background: #ef4444; }}
    .metric-card.shutter .metric-bar-fill {{ background: #f59e0b; }}
    .metric-card.rf123 .metric-bar-fill {{ background: #06b6d4; }}
    .metric-card.others .metric-bar-fill {{ background: #8b5cf6; }}
    .metric-card.total .metric-bar-fill {{ background: #10b981; }}

    /* Filters & Controls */
    .controls-panel {{
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: var(--radius);
      padding: 16px 20px;
      margin-bottom: 24px;
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
    }}

    .search-box {{
      position: relative;
      flex: 1;
      min-width: 260px;
    }}

    .search-box input {{
      width: 100%;
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      padding: 10px 14px 10px 38px;
      font-size: 14px;
      color: var(--text-main);
      outline: none;
      transition: border-color 0.2s;
    }}

    .search-box input:focus {{
      border-color: var(--border-focus);
    }}

    .search-box svg {{
      position: absolute;
      left: 12px;
      top: 50%;
      transform: translateY(-50%);
      width: 16px;
      height: 16px;
      fill: var(--text-muted);
    }}

    .filter-tabs {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }}

    .tab-btn {{
      background: transparent;
      border: 1px solid transparent;
      color: var(--text-muted);
      border-radius: 20px;
      padding: 6px 14px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }}

    .tab-btn:hover {{
      color: var(--text-main);
      background: rgba(255, 255, 255, 0.05);
    }}

    .tab-btn.active {{
      background: var(--bg-card);
      border-color: var(--border-color);
      color: var(--badge-text);
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    }}

    /* Projects Grid / List */
    .projects-container {{
      display: flex;
      flex-direction: column;
      gap: 16px;
    }}

    .project-card {{
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: var(--radius);
      padding: 22px;
      transition: all 0.2s ease;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }}

    .project-card:hover {{
      border-color: rgba(59, 130, 246, 0.4);
      background: var(--bg-card);
    }}

    .project-header {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: flex-start;
      gap: 12px;
      margin-bottom: 16px;
      padding-bottom: 14px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    }}

    .project-info {{
      flex: 1;
      min-width: 280px;
    }}

    .set-id-badge {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 14px;
      font-weight: 700;
      color: #93c5fd;
      background: rgba(59, 130, 246, 0.15);
      border: 1px solid rgba(59, 130, 246, 0.3);
      padding: 3px 10px;
      border-radius: 6px;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      cursor: pointer;
    }}

    .set-id-badge:hover {{
      background: rgba(59, 130, 246, 0.25);
    }}

    .project-title {{
      font-size: 16px;
      font-weight: 700;
      color: var(--text-main);
      margin-top: 8px;
    }}

    .meta-pills {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 8px;
    }}

    .pill {{
      font-size: 11px;
      font-weight: 600;
      padding: 3px 8px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.06);
      color: var(--text-muted);
      border: 1px solid rgba(255, 255, 255, 0.08);
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }}

    .pill.count {{
      background: rgba(16, 185, 129, 0.15);
      color: #34d399;
      border-color: rgba(16, 185, 129, 0.3);
    }}

    .pill.date {{
      background: rgba(245, 158, 11, 0.12);
      color: #fbbf24;
      border-color: rgba(245, 158, 11, 0.25);
    }}

    .project-actions {{
      display: flex;
      gap: 8px;
      align-items: center;
    }}

    /* Platforms Checklist Grid */
    .checklist-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 12px;
    }}

    .platform-item {{
      background: rgba(11, 15, 25, 0.5);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      padding: 14px 16px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      transition: all 0.2s ease;
      position: relative;
    }}

    .platform-item.checked {{
      background: rgba(16, 185, 129, 0.06);
      border-color: rgba(16, 185, 129, 0.35);
    }}

    .platform-top {{
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    .platform-name {{
      font-size: 14px;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .dot {{
      width: 10px;
      height: 10px;
      border-radius: 50%;
      display: inline-block;
    }}

    .dot.adobe {{ background: #ef4444; }}
    .dot.shutter {{ background: #f59e0b; }}
    .dot.rf123 {{ background: #06b6d4; }}
    .dot.others {{ background: #8b5cf6; }}

    .checkbox-label {{
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      user-select: none;
    }}

    .custom-check {{
      width: 20px;
      height: 20px;
      border: 2px solid var(--border-color);
      border-radius: 5px;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.2s;
      background: var(--bg-card);
    }}

    .platform-item.checked .custom-check {{
      background: var(--accent-emerald);
      border-color: var(--accent-emerald);
    }}

    .check-icon {{
      display: none;
      width: 12px;
      height: 12px;
      fill: #fff;
    }}

    .platform-item.checked .check-icon {{
      display: block;
    }}

    .platform-status {{
      font-size: 11px;
      font-weight: 600;
    }}

    .status-text {{
      color: var(--text-dim);
    }}

    .platform-item.checked .status-text {{
      color: var(--accent-emerald);
    }}

    .submission-date-input {{
      background: transparent;
      border: 1px dashed var(--border-color);
      border-radius: 4px;
      color: var(--text-muted);
      font-size: 11px;
      padding: 3px 6px;
      width: 100%;
      outline: none;
    }}

    .submission-date-input:focus {{
      border-color: var(--border-focus);
      color: var(--text-main);
    }}

    .platform-hint {{
      font-size: 11px;
      color: var(--text-dim);
      display: flex;
      align-items: center;
      gap: 4px;
    }}

    .platform-name-input {{
      background: transparent;
      border: 1px dashed var(--border-color);
      border-radius: 4px;
      color: var(--text-main);
      font-size: 12px;
      font-weight: 600;
      padding: 2px 6px;
      width: 120px;
    }}

    /* Notes section */
    .project-notes-box {{
      margin-top: 14px;
      padding-top: 12px;
      border-top: 1px dashed rgba(255, 255, 255, 0.08);
      display: none;
    }}

    .project-notes-box.open {{
      display: block;
    }}

    .notes-textarea {{
      width: 100%;
      background: var(--bg-primary);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      color: var(--text-main);
      font-size: 13px;
      padding: 8px 12px;
      resize: vertical;
      min-height: 60px;
      outline: none;
    }}

    .notes-textarea:focus {{
      border-color: var(--border-focus);
    }}

    /* Modal */
    .modal-overlay {{
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.7);
      backdrop-filter: blur(4px);
      z-index: 1000;
      justify-content: center;
      align-items: center;
      padding: 20px;
    }}

    .modal-overlay.open {{
      display: flex;
    }}

    .modal-card {{
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: var(--radius);
      width: 100%;
      max-width: 500px;
      padding: 24px;
      box-shadow: var(--shadow);
    }}

    .modal-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 18px;
    }}

    .modal-header h3 {{
      font-size: 18px;
      font-weight: 700;
    }}

    .form-group {{
      margin-bottom: 14px;
    }}

    .form-group label {{
      display: block;
      font-size: 12px;
      font-weight: 600;
      color: var(--text-muted);
      margin-bottom: 6px;
    }}

    .form-group input {{
      width: 100%;
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      color: var(--text-main);
      padding: 8px 12px;
      font-size: 14px;
      outline: none;
    }}

    /* Toast */
    .toast {{
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: var(--bg-card);
      border: 1px solid var(--accent-emerald);
      color: var(--text-main);
      padding: 12px 20px;
      border-radius: var(--radius-sm);
      box-shadow: var(--shadow);
      font-size: 13px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 10px;
      transform: translateY(100px);
      opacity: 0;
      transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
      z-index: 2000;
    }}

    .toast.show {{
      transform: translateY(0);
      opacity: 1;
    }}

    /* Empty state */
    .empty-state {{
      text-align: center;
      padding: 60px 20px;
      color: var(--text-muted);
      background: var(--bg-secondary);
      border: 1px dashed var(--border-color);
      border-radius: var(--radius);
    }}

    .empty-state h3 {{
      font-size: 18px;
      color: var(--text-main);
      margin-bottom: 6px;
    }}
  </style>
</head>
<body>

<div class="container">
  <!-- Header -->
  <header>
    <div class="header-title-group">
      <h1>
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="stroke: #38bdf8;">
          <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
          <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
          <line x1="12" y1="22.08" x2="12" y2="12"></line>
        </svg>
        Stock Submission Checklist
      </h1>
      <p>Automated stock pipeline submission tracker with persistent local storage for Adobe Stock, Shutterstock, 123RF &amp; agencies.</p>
    </div>
    <div class="header-actions">
      <button class="btn btn-primary" onclick="openAddModal()">
        <span>+ Add Set Manually</span>
      </button>
      <button class="btn" onclick="exportData()">
        <span>💾 Export Status (JSON)</span>
      </button>
      <button class="btn" onclick="document.getElementById('importFile').click()">
        <span>📥 Import Backup</span>
      </button>
      <input type="file" id="importFile" style="display:none;" accept=".json" onchange="importData(event)">
      <a href="https://github.com/armwoottipong/Stock_automation" target="_blank" class="btn">
        <span>GitHub Repo</span>
      </a>
    </div>
  </header>

  <!-- Metrics Bar -->
  <div class="metrics-grid">
    <div class="metric-card total">
      <div class="metric-label">
        <span>Total Projects</span>
        <span id="metricTotalAssets">0 Assets</span>
      </div>
      <div class="metric-value">
        <span id="metricTotalSets">0</span>
        <span class="metric-sub">sets</span>
      </div>
      <div class="metric-bar-bg"><div class="metric-bar-fill" id="barOverall" style="width: 0%;"></div></div>
    </div>

    <div class="metric-card adobe">
      <div class="metric-label">
        <span>Adobe Stock</span>
        <span id="metricAdobePercent">0%</span>
      </div>
      <div class="metric-value">
        <span id="metricAdobeCount">0</span>
        <span class="metric-sub" id="metricAdobeSub">/ 0 submitted</span>
      </div>
      <div class="metric-bar-bg"><div class="metric-bar-fill" id="barAdobe" style="width: 0%;"></div></div>
    </div>

    <div class="metric-card shutter">
      <div class="metric-label">
        <span>Shutterstock</span>
        <span id="metricShutterPercent">0%</span>
      </div>
      <div class="metric-value">
        <span id="metricShutterCount">0</span>
        <span class="metric-sub" id="metricShutterSub">/ 0 submitted</span>
      </div>
      <div class="metric-bar-bg"><div class="metric-bar-fill" id="barShutter" style="width: 0%;"></div></div>
    </div>

    <div class="metric-card rf123">
      <div class="metric-label">
        <span>123RF</span>
        <span id="metric123rfPercent">0%</span>
      </div>
      <div class="metric-value">
        <span id="metric123rfCount">0</span>
        <span class="metric-sub" id="metric123rfSub">/ 0 submitted</span>
      </div>
      <div class="metric-bar-bg"><div class="metric-bar-fill" id="bar123rf" style="width: 0%;"></div></div>
    </div>

    <div class="metric-card others">
      <div class="metric-label">
        <span>Others (อื่นๆ)</span>
        <span id="metricOthersPercent">0%</span>
      </div>
      <div class="metric-value">
        <span id="metricOthersCount">0</span>
        <span class="metric-sub" id="metricOthersSub">/ 0 submitted</span>
      </div>
      <div class="metric-bar-bg"><div class="metric-bar-fill" id="barOthers" style="width: 0%;"></div></div>
    </div>
  </div>

  <!-- Filters & Controls -->
  <div class="controls-panel">
    <div class="search-box">
      <svg viewBox="0 0 24 24"><path d="M21.71 20.29l-5.4-5.4A8.93 8.93 0 0 0 18 10a9 9 0 1 0-9 9 8.93 8.93 0 0 0 4.89-1.31l5.4 5.4a1 1 0 0 0 1.42 0 1 1 0 0 0 0-1.4zM4 10a7 7 0 1 1 7 7 7 7 0 0 1-7-7z"/></svg>
      <input type="text" id="searchInput" placeholder="Search by Set ID, subject, title, or notes..." oninput="handleSearch()">
    </div>

    <div class="filter-tabs">
      <button class="tab-btn active" onclick="setFilter('all', this)">All Projects</button>
      <button class="tab-btn" onclick="setFilter('pending_any', this)">⏳ Pending Submission</button>
      <button class="tab-btn" onclick="setFilter('fully_done', this)">✅ Fully Completed</button>
      <button class="tab-btn" onclick="setFilter('pending_adobe', this)">Adobe Pending</button>
      <button class="tab-btn" onclick="setFilter('pending_shutter', this)">Shutterstock Pending</button>
      <button class="tab-btn" onclick="setFilter('pending_123rf', this)">123RF Pending</button>
      <button class="tab-btn" onclick="setFilter('pending_others', this)">Others Pending</button>
    </div>
  </div>

  <!-- Projects List -->
  <div class="projects-container" id="projectsContainer">
    <!-- Populated by JS -->
  </div>
</div>

<!-- Modal: Add Custom Project -->
<div class="modal-overlay" id="addModal">
  <div class="modal-card">
    <div class="modal-header">
      <h3>Add New Project to Checklist</h3>
      <button class="btn btn-sm" onclick="closeAddModal()">✕</button>
    </div>
    <form id="addProjectForm" onsubmit="handleAddProject(event)">
      <div class="form-group">
        <label>Set ID (e.g. coffee_beans_500_2026-10-02_001)</label>
        <input type="text" id="newSetId" required placeholder="unique_set_id">
      </div>
      <div class="form-group">
        <label>Project Title / Description</label>
        <input type="text" id="newTitle" required placeholder="Roasted coffee beans isolated on white">
      </div>
      <div class="form-group">
        <label>Date (YYYY-MM-DD)</label>
        <input type="date" id="newDate">
      </div>
      <div class="form-group">
        <label>Total Asset Count</label>
        <input type="number" id="newCount" value="100" min="1">
      </div>
      <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:20px;">
        <button type="button" class="btn" onclick="closeAddModal()">Cancel</button>
        <button type="submit" class="btn btn-primary">Add Project</button>
      </div>
    </form>
  </div>
</div>

<!-- Toast notification -->
<div class="toast" id="toast">
  <span>✓</span>
  <span id="toastMsg">Status updated and saved to local storage</span>
</div>

<script>
  // Initial embedded roster of projects generated by pipeline
  const INITIAL_PROJECTS = {projects_json};

  const STORAGE_KEY = "stock_submission_checklist_v1";

  let appState = {{
    projects: [],
    submissions: {{}},
    currentFilter: "all",
    searchQuery: ""
  }};

  // Initialize
  function initApp() {{
    loadStorage();
    mergeProjects(INITIAL_PROJECTS);
    tryFetchLatestProjects();
    renderApp();
  }}

  // Load from browser localStorage
  function loadStorage() {{
    try {{
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {{
        const parsed = JSON.parse(raw);
        appState.submissions = parsed.submissions || {{}};
        if (Array.isArray(parsed.custom_projects)) {{
          mergeProjects(parsed.custom_projects);
        }}
      }}
    }} catch (e) {{
      console.error("Failed to parse localStorage", e);
    }}
  }}

  // Save to browser localStorage
  function saveStorage() {{
    try {{
      const customProjects = appState.projects.filter(p => p.is_custom);
      const dataToSave = {{
        version: 1,
        last_updated: new Date().toISOString(),
        submissions: appState.submissions,
        custom_projects: customProjects
      }};
      localStorage.setItem(STORAGE_KEY, JSON.stringify(dataToSave));
      showToast("Saved to local storage");
    }} catch (e) {{
      console.error("Failed to save to localStorage", e);
    }}
  }}

  function mergeProjects(newList) {{
    if (!Array.isArray(newList)) return;
    newList.forEach(item => {{
      const exists = appState.projects.find(p => p.id === item.id);
      if (!exists) {{
        appState.projects.push(item);
      }} else {{
        Object.assign(exists, item);
      }}
      // Ensure submissions entry exists
      if (!appState.submissions[item.id]) {{
        appState.submissions[item.id] = {{
          adobe_stock: {{ submitted: false, date: "" }},
          shutterstock: {{ submitted: false, date: "" }},
          "123rf": {{ submitted: false, date: "" }},
          others: {{ submitted: false, name: "Freepik / Vecteezy", date: "" }},
          notes: ""
        }};
      }}
    }});
  }}

  // Try to fetch projects.json if served via web/GitHub Pages
  async function tryFetchLatestProjects() {{
    try {{
      const res = await fetch("projects.json");
      if (res.ok) {{
        const remoteProjects = await res.json();
        mergeProjects(remoteProjects);
        renderApp();
      }}
    }} catch (e) {{
      // Offline file:/// mode, safely ignore
    }}
  }}

  // Get current timestamp format: YYYY-MM-DD HH:mm
  function getCurrentTimestamp() {{
    const now = new Date();
    const y = now.getFullYear();
    const m = String(now.getMonth() + 1).padStart(2, "0");
    const d = String(now.getDate()).padStart(2, "0");
    const hh = String(now.getHours()).padStart(2, "0");
    const mm = String(now.getMinutes()).padStart(2, "0");
    return `${{y}}-${{m}}-${{d}} ${{hh}}:${{mm}}`;
  }}

  // Toggle platform submission
  function togglePlatform(setId, platform) {{
    if (!appState.submissions[setId]) return;
    const item = appState.submissions[setId][platform];
    item.submitted = !item.submitted;
    if (item.submitted && !item.date) {{
      item.date = getCurrentTimestamp();
    }} else if (!item.submitted) {{
      item.date = "";
    }}
    saveStorage();
    renderApp();
  }}

  // Change submission date
  function updateDate(setId, platform, value) {{
    if (!appState.submissions[setId]) return;
    appState.submissions[setId][platform].date = value;
    saveStorage();
    renderMetrics();
  }}

  // Change custom others platform name
  function updateOthersName(setId, value) {{
    if (!appState.submissions[setId]) return;
    appState.submissions[setId].others.name = value;
    saveStorage();
  }}

  // Update notes
  function updateNotes(setId, value) {{
    if (!appState.submissions[setId]) return;
    appState.submissions[setId].notes = value;
    saveStorage();
  }}

  function toggleNotesBox(setId) {{
    const el = document.getElementById(`notesBox_${{setId}}`);
    if (el) el.classList.toggle("open");
  }}

  // Mark all platforms submitted for a project
  function markAllSubmitted(setId) {{
    if (!appState.submissions[setId]) return;
    const now = getCurrentTimestamp();
    ["adobe_stock", "shutterstock", "123rf", "others"].forEach(plat => {{
      appState.submissions[setId][plat].submitted = true;
      if (!appState.submissions[setId][plat].date) {{
        appState.submissions[setId][plat].date = now;
      }}
    }});
    saveStorage();
    renderApp();
  }}

  // Reset status for a project
  function resetProjectStatus(setId) {{
    if (!appState.submissions[setId]) return;
    if (!confirm(`Reset submission status for set ${{setId}}?`)) return;
    ["adobe_stock", "shutterstock", "123rf", "others"].forEach(plat => {{
      appState.submissions[setId][plat].submitted = false;
      appState.submissions[setId][plat].date = "";
    }});
    saveStorage();
    renderApp();
  }}

  // Copy set ID to clipboard
  function copySetId(setId) {{
    navigator.clipboard.writeText(setId).then(() => {{
      showToast(`Copied ${{setId}} to clipboard`);
    }}).catch(() => {{
      showToast(`Set ID: ${{setId}}`);
    }});
  }}

  // Toast
  function showToast(msg) {{
    const toast = document.getElementById("toast");
    const toastMsg = document.getElementById("toastMsg");
    toastMsg.textContent = msg;
    toast.classList.add("show");
    setTimeout(() => toast.classList.remove("show"), 2500);
  }}

  // Search & Filter
  function handleSearch() {{
    appState.searchQuery = document.getElementById("searchInput").value.trim().toLowerCase();
    renderProjectsList();
  }}

  function setFilter(filterName, btnEl) {{
    appState.currentFilter = filterName;
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    if (btnEl) btnEl.classList.add("active");
    renderProjectsList();
  }}

  // Add custom project
  function openAddModal() {{
    document.getElementById("newDate").value = new Date().toISOString().split("T")[0];
    document.getElementById("addModal").classList.add("open");
  }}

  function closeAddModal() {{
    document.getElementById("addModal").classList.remove("open");
  }}

  function handleAddProject(e) {{
    e.preventDefault();
    const setId = document.getElementById("newSetId").value.trim();
    const title = document.getElementById("newTitle").value.trim();
    const date = document.getElementById("newDate").value;
    const count = parseInt(document.getElementById("newCount").value, 10) || 100;

    if (!setId) return;

    const newProject = {{
      id: setId,
      title: title,
      date: date,
      image_count: count,
      packages: ["adobe_stock"],
      has_csv: true,
      has_white_jpg: true,
      has_transparent_png: true,
      is_custom: true
    }};

    mergeProjects([newProject]);
    saveStorage();
    closeAddModal();
    renderApp();
    showToast(`Added new project ${{setId}}`);
  }}

  // Export / Import
  function exportData() {{
    const customProjects = appState.projects.filter(p => p.is_custom);
    const dataToExport = {{
      version: 1,
      exported_at: new Date().toISOString(),
      submissions: appState.submissions,
      custom_projects: customProjects
    }};
    const blob = new Blob([JSON.stringify(dataToExport, null, 2)], {{ type: "application/json" }});
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `stock_submission_backup_${{new Date().toISOString().split("T")[0]}}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showToast("Downloaded checklist backup JSON");
  }}

  function importData(e) {{
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = function(event) {{
      try {{
        const imported = JSON.parse(event.target.result);
        if (imported.submissions) {{
          appState.submissions = Object.assign(appState.submissions, imported.submissions);
        }}
        if (Array.isArray(imported.custom_projects)) {{
          mergeProjects(imported.custom_projects);
        }}
        saveStorage();
        renderApp();
        showToast("Backup restored successfully!");
      }} catch (err) {{
        alert("Invalid JSON backup file");
      }}
    }};
    reader.readAsText(file);
    e.target.value = "";
  }}

  // Render Metrics
  function renderMetrics() {{
    const totalSets = appState.projects.length;
    let totalAssets = 0;
    let adobeCount = 0;
    let shutterCount = 0;
    let rf123Count = 0;
    let othersCount = 0;

    appState.projects.forEach(p => {{
      totalAssets += p.image_count || 0;
      const sub = appState.submissions[p.id] || {{}};
      if (sub.adobe_stock && sub.adobe_stock.submitted) adobeCount++;
      if (sub.shutterstock && sub.shutterstock.submitted) shutterCount++;
      if (sub["123rf"] && sub["123rf"].submitted) rf123Count++;
      if (sub.others && sub.others.submitted) othersCount++;
    }});

    document.getElementById("metricTotalSets").textContent = totalSets;
    document.getElementById("metricTotalAssets").textContent = `${{totalAssets.toLocaleString()}} Assets`;

    const calcPct = (cnt) => totalSets > 0 ? Math.round((cnt / totalSets) * 100) : 0;

    const adobePct = calcPct(adobeCount);
    document.getElementById("metricAdobeCount").textContent = adobeCount;
    document.getElementById("metricAdobeSub").textContent = `/ ${{totalSets}} submitted`;
    document.getElementById("metricAdobePercent").textContent = `${{adobePct}}%`;
    document.getElementById("barAdobe").style.width = `${{adobePct}}%`;

    const shutterPct = calcPct(shutterCount);
    document.getElementById("metricShutterCount").textContent = shutterCount;
    document.getElementById("metricShutterSub").textContent = `/ ${{totalSets}} submitted`;
    document.getElementById("metricShutterPercent").textContent = `${{shutterPct}}%`;
    document.getElementById("barShutter").style.width = `${{shutterPct}}%`;

    const rf123Pct = calcPct(rf123Count);
    document.getElementById("metric123rfCount").textContent = rf123Count;
    document.getElementById("metric123rfSub").textContent = `/ ${{totalSets}} submitted`;
    document.getElementById("metric123rfPercent").textContent = `${{rf123Pct}}%`;
    document.getElementById("bar123rf").style.width = `${{rf123Pct}}%`;

    const othersPct = calcPct(othersCount);
    document.getElementById("metricOthersCount").textContent = othersCount;
    document.getElementById("metricOthersSub").textContent = `/ ${{totalSets}} submitted`;
    document.getElementById("metricOthersPercent").textContent = `${{othersPct}}%`;
    document.getElementById("barOthers").style.width = `${{othersPct}}%`;

    const overallPct = totalSets > 0 ? Math.round(((adobeCount + shutterCount + rf123Count + othersCount) / (totalSets * 4)) * 100) : 0;
    document.getElementById("barOverall").style.width = `${{overallPct}}%`;
  }}

  // Filter check logic
  function matchFilter(project) {{
    const sub = appState.submissions[project.id] || {{}};
    const isAdobe = sub.adobe_stock && sub.adobe_stock.submitted;
    const isShutter = sub.shutterstock && sub.shutterstock.submitted;
    const is123rf = sub["123rf"] && sub["123rf"].submitted;
    const isOthers = sub.others && sub.others.submitted;

    if (appState.currentFilter === "all") return true;
    if (appState.currentFilter === "fully_done") return isAdobe && isShutter && is123rf && isOthers;
    if (appState.currentFilter === "pending_any") return !(isAdobe && isShutter && is123rf && isOthers);
    if (appState.currentFilter === "pending_adobe") return !isAdobe;
    if (appState.currentFilter === "pending_shutter") return !isShutter;
    if (appState.currentFilter === "pending_123rf") return !is123rf;
    if (appState.currentFilter === "pending_others") return !isOthers;
    return true;
  }}

  // Render Projects List
  function renderProjectsList() {{
    const container = document.getElementById("projectsContainer");
    const q = appState.searchQuery;

    const filtered = appState.projects.filter(p => {{
      const sub = appState.submissions[p.id] || {{}};
      const notes = (sub.notes || "").toLowerCase();
      const text = `${{p.id}} ${{p.title}} ${{p.date}} ${{notes}}`.toLowerCase();
      const matchesSearch = !q || text.includes(q);
      const matchesFilter = matchFilter(p);
      return matchesSearch && matchesFilter;
    }});

    if (filtered.length === 0) {{
      container.innerHTML = `
        <div class="empty-state">
          <h3>No matching stock projects found</h3>
          <p>Try modifying your search or filter settings, or add a new project above.</p>
        </div>
      `;
      return;
    }}

    container.innerHTML = filtered.map(p => {{
      const sub = appState.submissions[p.id] || {{}};
      const adobe = sub.adobe_stock || {{ submitted: false, date: "" }};
      const shutter = sub.shutterstock || {{ submitted: false, date: "" }};
      const rf123 = sub["123rf"] || {{ submitted: false, date: "" }};
      const others = sub.others || {{ submitted: false, name: "Freepik / Vecteezy", date: "" }};
      const notes = sub.notes || "";

      return `
        <div class="project-card" id="card_${{p.id}}">
          <div class="project-header">
            <div class="project-info">
              <span class="set-id-badge" onclick="copySetId('${{p.id}}')" title="Click to copy set ID">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                ${{p.id}}
              </span>
              <div class="project-title">${{p.title}}</div>
              <div class="meta-pills">
                <span class="pill count">📊 ${{p.image_count}} Items</span>
                <span class="pill date">📅 ${{p.date}}</span>
                ${{p.has_transparent_png ? '<span class="pill">PNG Cutout</span>' : ''}}
                ${{p.has_white_jpg ? '<span class="pill">White JPEG</span>' : ''}}
                ${{p.has_csv ? '<span class="pill">CSV Catalog</span>' : ''}}
              </div>
            </div>

            <div class="project-actions">
              <button class="btn btn-sm btn-success" onclick="markAllSubmitted('${{p.id}}')" title="Mark all platforms as submitted">
                ✓ All Done
              </button>
              <button class="btn btn-sm" onclick="toggleNotesBox('${{p.id}}')">
                📝 Notes
              </button>
              <button class="btn btn-sm" onclick="resetProjectStatus('${{p.id}}')" title="Reset platform checkmarks">
                ↺ Reset
              </button>
            </div>
          </div>

          <!-- Platforms Checklist Grid -->
          <div class="checklist-grid">
            <!-- Adobe Stock -->
            <div class="platform-item ${{adobe.submitted ? 'checked' : ''}}">
              <div class="platform-top">
                <div class="platform-name">
                  <span class="dot adobe"></span>
                  Adobe Stock
                </div>
                <div class="checkbox-label" onclick="togglePlatform('${{p.id}}', 'adobe_stock')">
                  <div class="custom-check">
                    <svg class="check-icon" viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
                  </div>
                </div>
              </div>
              <div class="platform-status">
                <span class="status-text">${{adobe.submitted ? '✓ Submitted' : '○ Not Submitted'}}</span>
              </div>
              <input type="text" class="submission-date-input" placeholder="Date: YYYY-MM-DD HH:mm" value="${{adobe.date || ''}}" onchange="updateDate('${{p.id}}', 'adobe_stock', this.value)">
              <div class="platform-hint">⚠️ Generative AI checkbox required</div>
            </div>

            <!-- Shutterstock -->
            <div class="platform-item ${{shutter.submitted ? 'checked' : ''}}">
              <div class="platform-top">
                <div class="platform-name">
                  <span class="dot shutter"></span>
                  Shutterstock
                </div>
                <div class="checkbox-label" onclick="togglePlatform('${{p.id}}', 'shutterstock')">
                  <div class="custom-check">
                    <svg class="check-icon" viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
                  </div>
                </div>
              </div>
              <div class="platform-status">
                <span class="status-text">${{shutter.submitted ? '✓ Submitted' : '○ Not Submitted'}}</span>
              </div>
              <input type="text" class="submission-date-input" placeholder="Date: YYYY-MM-DD HH:mm" value="${{shutter.date || ''}}" onchange="updateDate('${{p.id}}', 'shutterstock', this.value)">
              <div class="platform-hint">ℹ️ Camera photo / policy check</div>
            </div>

            <!-- 123RF -->
            <div class="platform-item ${{rf123.submitted ? 'checked' : ''}}">
              <div class="platform-top">
                <div class="platform-name">
                  <span class="dot rf123"></span>
                  123RF
                </div>
                <div class="checkbox-label" onclick="togglePlatform('${{p.id}}', '123rf')">
                  <div class="custom-check">
                    <svg class="check-icon" viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
                  </div>
                </div>
              </div>
              <div class="platform-status">
                <span class="status-text">${{rf123.submitted ? '✓ Submitted' : '○ Not Submitted'}}</span>
              </div>
              <input type="text" class="submission-date-input" placeholder="Date: YYYY-MM-DD HH:mm" value="${{rf123.date || ''}}" onchange="updateDate('${{p.id}}', '123rf', this.value)">
              <div class="platform-hint">Standard contributor batch</div>
            </div>

            <!-- Others -->
            <div class="platform-item ${{others.submitted ? 'checked' : ''}}">
              <div class="platform-top">
                <div class="platform-name">
                  <span class="dot others"></span>
                  <input type="text" class="platform-name-input" value="${{others.name || 'Freepik'}}" onchange="updateOthersName('${{p.id}}', this.value)" title="Click to rename agency">
                </div>
                <div class="checkbox-label" onclick="togglePlatform('${{p.id}}', 'others')">
                  <div class="custom-check">
                    <svg class="check-icon" viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
                  </div>
                </div>
              </div>
              <div class="platform-status">
                <span class="status-text">${{others.submitted ? '✓ Submitted' : '○ Not Submitted'}}</span>
              </div>
              <input type="text" class="submission-date-input" placeholder="Date: YYYY-MM-DD HH:mm" value="${{others.date || ''}}" onchange="updateDate('${{p.id}}', 'others', this.value)">
              <div class="platform-hint">Other stock portals</div>
            </div>
          </div>

          <!-- Notes Area -->
          <div class="project-notes-box ${{notes ? 'open' : ''}}" id="notesBox_${{p.id}}">
            <textarea class="notes-textarea" placeholder="Add submission notes (e.g. batch ID, FTP submission date, acceptance details)..." onchange="updateNotes('${{p.id}}', this.value)">${{notes}}</textarea>
          </div>
        </div>
      `;
    }}).join("");
  }}

  function renderApp() {{
    renderMetrics();
    renderProjectsList();
  }}

  // Start on load
  document.addEventListener("DOMContentLoaded", initApp);
</script>
</body>
</html>
"""


def update_checklist(
    output_dir: Path | None = None,
    docs_dir: Path | None = None,
    push: bool = False,
    set_id: str | None = None,
    verbose: bool = True,
) -> tuple[Path, Path]:
    """Scan output sets and write docs/projects.json and docs/index.html."""
    out_path = output_dir or DEFAULT_OUTPUT
    docs_path = docs_dir or DEFAULT_DOCS

    docs_path.mkdir(parents=True, exist_ok=True)

    projects = scan_output_sets(out_path)

    # If specific set_id provided and not found in scan (e.g. still in progress), add placeholder
    if set_id and not any(p["id"] == set_id for p in projects):
        projects.insert(0, {
            "id": set_id,
            "date": "Pending",
            "title": set_id.replace("_", " ").title(),
            "image_count": 0,
            "packages": [],
            "has_csv": False,
            "has_white_jpg": False,
            "has_transparent_png": False,
            "has_contact_sheet": False,
            "keywords_sample": [],
        })

    # 1. Write projects.json (both docs/ and root for universal GitHub Pages support)
    json_path = docs_path / "projects.json"
    json_text = json.dumps(projects, indent=2, ensure_ascii=False) + "\n"
    json_path.write_text(json_text, encoding="utf-8")
    if docs_path.resolve() != ROOT.resolve():
        (ROOT / "projects.json").write_text(json_text, encoding="utf-8")

    # 2. Write index.html (both docs/ and root)
    html_path = docs_path / "index.html"
    html_content = build_checklist_html(projects)
    html_path.write_text(html_content, encoding="utf-8")
    if docs_path.resolve() != ROOT.resolve():
        (ROOT / "index.html").write_text(html_content, encoding="utf-8")

    if verbose:
        print(f"Checklist updated: {len(projects)} projects recorded.")
        print(f"  JSON: {json_path} & {ROOT / 'projects.json'}")
        print(f"  HTML: {html_path} & {ROOT / 'index.html'}")

    # 3. Optional Git commit & push
    if push:
        try:
            print("\nDeploying checklist to GitHub Pages (git push)...", flush=True)
            subprocess.run(["git", "add", "docs/", ".github/", "index.html", "projects.json"], cwd=ROOT, check=True)
            commit_msg = f"Update stock submission checklist ({len(projects)} sets)"
            # Check if there are staged changes
            res_diff = subprocess.run(["git", "diff", "--staged", "--quiet"], cwd=ROOT)
            if res_diff.returncode != 0:
                subprocess.run(["git", "commit", "-m", commit_msg], cwd=ROOT, check=True)
                subprocess.run(["git", "push", "origin", "main"], cwd=ROOT, check=True)
                print("SUCCESS: Checklist pushed to origin/main. GitHub Pages will build and deploy automatically!", flush=True)
            else:
                print("No changes to commit (checklist already up to date).", flush=True)
        except Exception as e:
            print(f"Warning: Git push encountered an issue: {e}", file=sys.stderr)

    return json_path, html_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--set-id", type=str, help="Specific set ID that was finalized")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT, help="Path to output directory")
    parser.add_argument("--docs-dir", type=Path, default=DEFAULT_DOCS, help="Path to docs directory")
    parser.add_argument("--push", action="store_true", help="Commit and push updated checklist to GitHub Pages")
    parser.add_argument("--quiet", action="store_true", help="Quiet output")
    args = parser.parse_args()

    update_checklist(
        output_dir=args.output_dir,
        docs_dir=args.docs_dir,
        push=args.push,
        set_id=args.set_id,
        verbose=not args.quiet,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
