"""Generate and update the stock submission checklist HTML and JSON.

This script scans output/ sets, compiles project records, generates a minimal
editorial HTML checklist with localStorage persistence, and optionally deploys/pushes to GitHub Pages.
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
    """Generate a clean, minimal editorial todo list checklist with localStorage persistence."""
    projects_json = json.dumps(projects, ensure_ascii=False, indent=2)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Stock Submission Checklist | Minimal Editorial</title>
  <!-- Firebase SDK -->
  <script src="https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js"></script>
  <script src="https://www.gstatic.com/firebasejs/10.12.0/firebase-firestore-compat.js"></script>
  <style>
    :root {{
      --bg: #faf9f6;
      --surface: #ffffff;
      --border: #e8e6e1;
      --border-subtle: #f0eee9;
      --text: #1a1b1e;
      --text-muted: #74767e;
      --text-dim: #9da0a8;
      --accent: #111214;
      --pill-checked-bg: #1c1d21;
      --pill-checked-text: #ffffff;
      --pill-unchecked-bg: #f4f3ef;
      --pill-unchecked-text: #4a4c54;
      --pill-border: #e2e0da;
      --tag-bg: #eceae4;
      --tag-text: #5c5e66;
    }}

    @media (prefers-color-scheme: dark) {{
      :root {{
        --bg: #0f1013;
        --surface: #15171b;
        --border: #23252b;
        --border-subtle: #1b1d22;
        --text: #edecee;
        --text-muted: #8c8f99;
        --text-dim: #5c5f69;
        --accent: #f2f2f4;
        --pill-checked-bg: #edecee;
        --pill-checked-text: #111214;
        --pill-unchecked-bg: #1a1c22;
        --pill-unchecked-text: #a8abb6;
        --pill-border: #292c34;
        --tag-bg: #1e2027;
        --tag-text: #8c8f99;
      }}
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    body {{
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      line-height: 1.5;
      padding: 40px 20px 80px;
      -webkit-font-smoothing: antialiased;
    }}

    .container {{
      max-width: 860px;
      margin: 0 auto;
    }}

    /* Minimal Editorial Header */
    header {{
      padding-bottom: 28px;
      border-bottom: 1px solid var(--border);
      margin-bottom: 24px;
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      flex-wrap: wrap;
      gap: 16px;
    }}

    .title-group h1 {{
      font-family: "Newsreader", "Charter", "Georgia", "Iowan Old Style", serif;
      font-size: 32px;
      font-weight: 500;
      letter-spacing: -0.5px;
      color: var(--text);
    }}

    .title-group p {{
      color: var(--text-muted);
      font-size: 14px;
      margin-top: 4px;
    }}

    .header-links {{
      display: flex;
      gap: 12px;
      align-items: center;
    }}

    .btn-link {{
      background: transparent;
      border: 1px solid var(--border);
      color: var(--text);
      font-size: 13px;
      padding: 6px 14px;
      border-radius: 6px;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s ease;
    }}

    .btn-link:hover {{
      border-color: var(--text-muted);
      background: var(--surface);
    }}

    /* Minimal Controls */
    .controls-bar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
      margin-bottom: 20px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--border-subtle);
    }}

    .filter-group {{
      display: flex;
      gap: 16px;
      font-size: 14px;
    }}

    .filter-item {{
      background: none;
      border: none;
      color: var(--text-muted);
      cursor: pointer;
      padding: 2px 0;
      font-size: 13px;
      font-weight: 500;
      position: relative;
    }}

    .filter-item:hover {{
      color: var(--text);
    }}

    .filter-item.active {{
      color: var(--text);
      font-weight: 600;
    }}

    .filter-item.active::after {{
      content: "";
      position: absolute;
      bottom: -6px;
      left: 0;
      width: 100%;
      height: 1.5px;
      background: var(--text);
    }}

    .search-input {{
      background: transparent;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 6px 12px;
      font-size: 13px;
      color: var(--text);
      outline: none;
      width: 200px;
      transition: all 0.2s;
    }}

    .search-input:focus {{
      border-color: var(--text-muted);
      width: 240px;
      background: var(--surface);
    }}

    /* Todo List */
    .todo-list {{
      display: flex;
      flex-direction: column;
    }}

    .todo-row {{
      padding: 20px 0;
      border-bottom: 1px solid var(--border-subtle);
      transition: background 0.1s ease;
    }}

    .todo-row:last-child {{
      border-bottom: none;
    }}

    .todo-meta-line {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;
      font-size: 12px;
      color: var(--text-muted);
    }}

    .set-id {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, monospace;
      font-size: 12px;
      color: var(--text-muted);
      cursor: pointer;
    }}

    .set-id:hover {{
      color: var(--text);
      text-decoration: underline;
    }}

    .todo-title {{
      font-size: 16px;
      font-weight: 600;
      color: var(--text);
      margin-bottom: 12px;
      line-height: 1.4;
    }}

    .todo-row.all-done .todo-title {{
      color: var(--text-muted);
      text-decoration: line-through;
    }}

    /* Minimal Checkbox Pills */
    .platforms-checklist {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }}

    .check-pill {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 5px 12px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      user-select: none;
      background: var(--pill-unchecked-bg);
      color: var(--pill-unchecked-text);
      border: 1px solid var(--pill-border);
      transition: all 0.15s ease;
    }}

    .check-pill:hover {{
      border-color: var(--text-muted);
    }}

    .check-pill.checked {{
      background: var(--pill-checked-bg);
      color: var(--pill-checked-text);
      border-color: transparent;
    }}

    .check-pill input {{
      display: none;
    }}

    .check-icon {{
      width: 12px;
      height: 12px;
      stroke-width: 2.5;
      stroke: currentColor;
      fill: none;
      display: none;
    }}

    .check-pill.checked .check-icon {{
      display: inline-block;
    }}

    .sub-date {{
      font-size: 11px;
      opacity: 0.75;
      margin-left: 2px;
    }}

    /* Notes Drawer / Toggle */
    .row-footer {{
      margin-top: 10px;
      display: flex;
      justify-content: flex-end;
      gap: 12px;
    }}

    .row-btn {{
      background: none;
      border: none;
      color: var(--text-dim);
      font-size: 11px;
      cursor: pointer;
      padding: 0;
    }}

    .row-btn:hover {{
      color: var(--text);
      text-decoration: underline;
    }}

    .row-notes {{
      margin-top: 8px;
      display: none;
    }}

    .row-notes.open {{
      display: block;
    }}

    .notes-input {{
      width: 100%;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 6px 10px;
      font-size: 12px;
      color: var(--text);
      outline: none;
    }}

    /* Settings Modal */
    .modal-overlay {{
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.45);
      backdrop-filter: blur(2px);
      z-index: 100;
      justify-content: center;
      align-items: center;
      padding: 20px;
    }}

    .modal-overlay.open {{
      display: flex;
    }}

    .modal-box {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      width: 100%;
      max-width: 440px;
      padding: 24px;
      box-shadow: 0 16px 36px rgba(0, 0, 0, 0.2);
    }}

    .modal-title {{
      font-size: 18px;
      font-weight: 600;
      margin-bottom: 4px;
    }}

    .modal-desc {{
      font-size: 13px;
      color: var(--text-muted);
      margin-bottom: 18px;
    }}

    .platform-tags {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 16px;
    }}

    .platform-tag {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: var(--tag-bg);
      color: var(--tag-text);
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 500;
    }}

    .remove-tag {{
      cursor: pointer;
      opacity: 0.6;
      font-weight: bold;
    }}

    .remove-tag:hover {{
      opacity: 1;
    }}

    .add-platform-form {{
      display: flex;
      gap: 8px;
      margin-bottom: 20px;
    }}

    .add-input {{
      flex: 1;
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 7px 12px;
      font-size: 13px;
      color: var(--text);
      outline: none;
    }}

    .btn-add {{
      background: var(--accent);
      color: var(--bg);
      border: none;
      border-radius: 6px;
      padding: 7px 14px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
    }}

    .modal-actions {{
      display: flex;
      justify-content: flex-end;
    }}

    /* Toast */
    .toast {{
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: var(--surface);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 8px 16px;
      border-radius: 6px;
      font-size: 12px;
      box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
      opacity: 0;
      transform: translateY(12px);
      transition: all 0.2s ease;
      pointer-events: none;
    }}

    .sync-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 6px;
    }}

    .sync-dot {{
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #10b981;
    }}

    .sync-dot.offline {{
      background: #eab308;
    }}

    .toast.show {{
      opacity: 1;
      transform: translateY(0);
    }}
  </style>
</head>
<body>

<div class="container">
  <!-- Minimal Header -->
  <header>
    <div class="title-group">
      <h1>Stock Submissions</h1>
      <p id="statusCounter">7 projects · microstock dispatch checklist</p>
      <div class="sync-badge">
        <span class="sync-dot" id="syncDot"></span>
        <span id="syncText">Connecting to cloud...</span>
      </div>
    </div>
    <div class="header-links">
      <button class="btn-link" onclick="openSettings()">⚙ Platforms</button>
      <button class="btn-link" onclick="exportData()">💾 Backup</button>
      <a href="https://github.com/armwoottipong/Stock_automation" target="_blank" class="btn-link">GitHub</a>
    </div>
  </header>

  <!-- Controls Bar -->
  <div class="controls-bar">
    <div class="filter-group">
      <button class="filter-item active" onclick="setFilter('all', this)">All</button>
      <button class="filter-item" onclick="setFilter('pending', this)">Pending</button>
      <button class="filter-item" onclick="setFilter('completed', this)">Completed</button>
    </div>
    <input type="text" class="search-input" id="searchInput" placeholder="Search projects..." oninput="handleSearch()">
  </div>

  <!-- Todo List -->
  <div class="todo-list" id="todoList">
    <!-- Populated by JavaScript -->
  </div>
</div>

<!-- Settings Modal -->
<div class="modal-overlay" id="settingsModal" onclick="handleOverlayClick(event)">
  <div class="modal-box">
    <div class="modal-title">Tracked Agencies</div>
    <div class="modal-desc">Configure platforms tracked on your submission checklist.</div>

    <div class="platform-tags" id="platformTagsList">
      <!-- Tag chips populated by JS -->
    </div>

    <form class="add-platform-form" onsubmit="handleAddPlatform(event)">
      <input type="text" class="add-input" id="newPlatformInput" placeholder="Add agency (e.g. Freepik, Vecteezy, Others)" required>
      <button type="submit" class="btn-add">+ Add</button>
    </form>

    <div id="restoreSection" style="margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--border); display: none;">
      <div style="font-size: 13px; font-weight: 600; margin-bottom: 4px;">Removed Projects</div>
      <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 8px;">Hidden from checklist. Click restore to put back in list.</div>
      <div id="deletedList" style="display: flex; flex-direction: column; gap: 6px; max-height: 140px; overflow-y: auto;"></div>
    </div>

    <div class="modal-actions" style="margin-top: 16px;">
      <button class="btn-link" onclick="closeSettings()">Done</button>
    </div>
  </div>
</div>

<div class="toast" id="toast">Saved to local storage</div>

<script>
  // Initial projects embedded by pipeline
  const INITIAL_PROJECTS = {projects_json};

  // Default initial agencies: Adobe Stock, Shutterstock, 123RF
  const DEFAULT_PLATFORMS = ["Adobe Stock", "Shutterstock", "123RF"];

  // LocalStorage keys
  const STORAGE_KEY = "stock_submission_checklist_v1";
  const PLATFORMS_KEY = "stock_configured_platforms_v1";
  const DELETED_KEY = "stock_deleted_projects_v1";

  // Firebase configuration
  const firebaseConfig = {{
    apiKey: "AIzaSyDz7Dkve8Kh0JD3LXzGK1iVB3PFnlUNhCE",
    authDomain: "stock-checklist-57743.firebaseapp.com",
    projectId: "stock-checklist-57743",
    storageBucket: "stock-checklist-57743.firebasestorage.app",
    messagingSenderId: "1073765326022",
    appId: "1:1073765326022:web:dba9769de45523d0e30bc7",
    measurementId: "G-77202SNTD4"
  }};

  let firestoreDb = null;
  let isCloudSyncing = false;

  let appState = {{
    projects: [],
    platforms: [...DEFAULT_PLATFORMS],
    submissions: {{}},
    deleted_projects: [],
    currentFilter: "all",
    searchQuery: ""
  }};

  function initApp() {{
    loadPlatforms();
    loadSubmissions();
    loadDeletedProjects();
    mergeProjects(INITIAL_PROJECTS);
    tryFetchProjects();
    renderApp();
    initFirebase();
  }}

  function loadDeletedProjects() {{
    try {{
      const raw = localStorage.getItem(DELETED_KEY);
      if (raw) {{
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) {{
          appState.deleted_projects = parsed;
        }}
      }}
    }} catch (e) {{
      console.error(e);
    }}
  }}

  function saveDeletedProjects() {{
    try {{
      localStorage.setItem(DELETED_KEY, JSON.stringify(appState.deleted_projects));
      pushToCloud();
    }} catch (e) {{
      console.error(e);
    }}
  }}

  function deleteProject(setId) {{
    if (!confirm(`Are you sure you want to remove "${{setId}}" from the checklist?`)) return;
    if (!appState.deleted_projects.includes(setId)) {{
      appState.deleted_projects.push(setId);
    }}
    saveDeletedProjects();
    showToast(`Removed ${{setId}}`);
    renderApp();
  }}

  function restoreProject(setId) {{
    appState.deleted_projects = appState.deleted_projects.filter(id => id !== setId);
    saveDeletedProjects();
    renderDeletedList();
    renderApp();
    showToast(`Restored ${{setId}}`);
  }}

  function initFirebase() {{
    try {{
      if (typeof firebase !== "undefined" && firebaseConfig && firebaseConfig.apiKey) {{
        if (!firebase.apps.length) {{
          firebase.initializeApp(firebaseConfig);
        }}
        firestoreDb = firebase.firestore();

        const docRef = firestoreDb.collection("stock_checklist").doc("state");
        docRef.onSnapshot((doc) => {{
          if (doc.exists) {{
            const data = doc.data();
            isCloudSyncing = true;
            if (data.submissions) {{
              appState.submissions = Object.assign(appState.submissions, data.submissions);
              localStorage.setItem(STORAGE_KEY, JSON.stringify({{ version: 2, submissions: appState.submissions }}));
            }}
            if (Array.isArray(data.platforms) && data.platforms.length > 0) {{
              appState.platforms = data.platforms;
              localStorage.setItem(PLATFORMS_KEY, JSON.stringify(appState.platforms));
            }}
            if (Array.isArray(data.deleted_projects)) {{
              appState.deleted_projects = data.deleted_projects;
              localStorage.setItem(DELETED_KEY, JSON.stringify(appState.deleted_projects));
            }}
            isCloudSyncing = false;
            setSyncStatus(true, "Firebase Real-time Synced");
            renderApp();
          }} else {{
            pushToCloud();
            setSyncStatus(true, "Firebase Real-time Synced");
          }}
        }}, (err) => {{
          console.warn("Firestore error:", err.message);
          setSyncStatus(false, "Local Cache (Enable Firestore in Test Mode)");
        }});
      }} else {{
        setSyncStatus(false, "Local Cache");
      }}
    }} catch (e) {{
      console.warn("Firebase init error:", e);
      setSyncStatus(false, "Local Cache");
    }}
  }}

  function setSyncStatus(isLive, label) {{
    const dot = document.getElementById("syncDot");
    const text = document.getElementById("syncText");
    if (dot && text) {{
      if (isLive) {{
        dot.className = "sync-dot";
      }} else {{
        dot.className = "sync-dot offline";
      }}
      text.textContent = label;
    }}
  }}

  function pushToCloud() {{
    if (!firestoreDb || isCloudSyncing) return;
    try {{
      firestoreDb.collection("stock_checklist").doc("state").set({{
        submissions: appState.submissions,
        platforms: appState.platforms,
        deleted_projects: appState.deleted_projects,
        last_updated: new Date().toISOString()
      }}, {{ merge: true }}).catch(err => {{
        console.warn("Cloud push warning:", err.message);
      }});
    }} catch (e) {{
      console.error(e);
    }}
  }}

  function loadPlatforms() {{
    try {{
      const raw = localStorage.getItem(PLATFORMS_KEY);
      if (raw) {{
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed) && parsed.length > 0) {{
          appState.platforms = parsed;
        }}
      }}
    }} catch (e) {{
      console.error(e);
    }}
  }}

  function savePlatforms() {{
    try {{
      localStorage.setItem(PLATFORMS_KEY, JSON.stringify(appState.platforms));
      showToast("Agencies updated");
      pushToCloud();
    }} catch (e) {{
      console.error(e);
    }}
  }}

  function loadSubmissions() {{
    try {{
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {{
        const parsed = JSON.parse(raw);
        appState.submissions = parsed.submissions || parsed || {{}};
      }}
    }} catch (e) {{
      console.error(e);
    }}
  }}

  function saveSubmissions() {{
    try {{
      localStorage.setItem(STORAGE_KEY, JSON.stringify({{
        version: 2,
        submissions: appState.submissions
      }}));
      showToast("Saved to local storage");
      pushToCloud();
    }} catch (e) {{
      console.error(e);
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
      if (!appState.submissions[item.id]) {{
        appState.submissions[item.id] = {{ checks: {{}}, notes: "" }};
      }}
    }});
  }}

  async function tryFetchProjects() {{
    try {{
      const res = await fetch("projects.json");
      if (res.ok) {{
        const data = await res.json();
        mergeProjects(data);
        renderApp();
      }}
    }} catch (e) {{}}
  }}

  function togglePlatform(setId, platform) {{
    if (!appState.submissions[setId]) {{
      appState.submissions[setId] = {{ checks: {{}}, notes: "" }};
    }}
    const checks = appState.submissions[setId].checks || {{}};
    const cur = checks[platform] || {{ submitted: false, date: "" }};
    
    if (cur.submitted) {{
      checks[platform] = {{ submitted: false, date: "" }};
    }} else {{
      const now = new Date();
      const dateStr = `${{now.getMonth() + 1}}/${{now.getDate()}}`;
      checks[platform] = {{ submitted: true, date: dateStr }};
    }}
    appState.submissions[setId].checks = checks;
    saveSubmissions();
    renderApp();
  }}

  function isSetComplete(setId) {{
    const checks = (appState.submissions[setId] && appState.submissions[setId].checks) || {{}};
    return appState.platforms.length > 0 && appState.platforms.every(p => checks[p] && checks[p].submitted);
  }}

  function toggleNotes(setId) {{
    const el = document.getElementById(`notes_${{setId}}`);
    if (el) el.classList.toggle("open");
  }}

  function updateNotes(setId, val) {{
    if (!appState.submissions[setId]) appState.submissions[setId] = {{ checks: {{}}, notes: "" }};
    appState.submissions[setId].notes = val;
    saveSubmissions();
  }}

  function copySetId(setId) {{
    navigator.clipboard.writeText(setId).then(() => {{
      showToast(`Copied ${{setId}}`);
    }}).catch(() => {{}});
  }}

  function setFilter(type, btn) {{
    appState.currentFilter = type;
    document.querySelectorAll(".filter-item").forEach(b => b.classList.remove("active"));
    if (btn) btn.classList.add("active");
    renderList();
  }}

  function handleSearch() {{
    appState.searchQuery = document.getElementById("searchInput").value.trim().toLowerCase();
    renderList();
  }}

  // Settings Modal Functions
  function openSettings() {{
    renderPlatformTags();
    renderDeletedList();
    document.getElementById("settingsModal").classList.add("open");
  }}

  function renderDeletedList() {{
    const sec = document.getElementById("restoreSection");
    const list = document.getElementById("deletedList");
    if (!sec || !list) return;
    if (appState.deleted_projects.length === 0) {{
      sec.style.display = "none";
      return;
    }}
    sec.style.display = "block";
    list.innerHTML = appState.deleted_projects.map(id => `
      <div style="display: flex; justify-content: space-between; align-items: center; font-size: 12px; background: var(--bg); padding: 5px 8px; border-radius: 4px; border: 1px solid var(--border);">
        <span style="font-family: monospace; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 250px;">${{id}}</span>
        <button class="row-btn" style="color: var(--accent); font-weight: 600;" onclick="restoreProject('${{id}}')">Restore</button>
      </div>
    `).join("");
  }}

  function closeSettings() {{
    document.getElementById("settingsModal").classList.remove("open");
  }}

  function handleOverlayClick(e) {{
    if (e.target.id === "settingsModal") closeSettings();
  }}

  function renderPlatformTags() {{
    const list = document.getElementById("platformTagsList");
    list.innerHTML = appState.platforms.map((plat, idx) => `
      <div class="platform-tag">
        <span>${{plat}}</span>
        ${{appState.platforms.length > 1 ? `<span class="remove-tag" onclick="removePlatform(${{idx}})">✕</span>` : ''}}
      </div>
    `).join("");
  }}

  function handleAddPlatform(e) {{
    e.preventDefault();
    const input = document.getElementById("newPlatformInput");
    const name = input.value.trim();
    if (name && !appState.platforms.includes(name)) {{
      appState.platforms.push(name);
      savePlatforms();
      renderPlatformTags();
      renderApp();
      input.value = "";
    }}
  }}

  function removePlatform(idx) {{
    appState.platforms.splice(idx, 1);
    savePlatforms();
    renderPlatformTags();
    renderApp();
  }}

  function exportData() {{
    const data = {{
      version: 2,
      exported_at: new Date().toISOString(),
      platforms: appState.platforms,
      submissions: appState.submissions,
      deleted_projects: appState.deleted_projects
    }};
    const blob = new Blob([JSON.stringify(data, null, 2)], {{ type: "application/json" }});
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `stock_checklist_backup.json`;
    a.click();
    URL.revokeObjectURL(url);
    showToast("Downloaded backup JSON");
  }}

  function showToast(msg) {{
    const toast = document.getElementById("toast");
    toast.textContent = msg;
    toast.classList.add("show");
    setTimeout(() => toast.classList.remove("show"), 2000);
  }}

  function renderList() {{
    const container = document.getElementById("todoList");
    const q = appState.searchQuery;

    const filtered = appState.projects.filter(p => {{
      if (appState.deleted_projects.includes(p.id)) return false;
      const sub = appState.submissions[p.id] || {{}};
      const complete = isSetComplete(p.id);
      const text = `${{p.id}} ${{p.title}} ${{sub.notes || ''}}`.toLowerCase();
      const matchesSearch = !q || text.includes(q);

      if (!matchesSearch) return false;
      if (appState.currentFilter === "pending") return !complete;
      if (appState.currentFilter === "completed") return complete;
      return true;
    }});

    if (filtered.length === 0) {{
      container.innerHTML = `<div style="padding:40px 0; color:var(--text-muted); font-size:14px;">No matching stock sets found.</div>`;
      return;
    }}

    container.innerHTML = filtered.map(p => {{
      const sub = appState.submissions[p.id] || {{ checks: {{}}, notes: "" }};
      const checks = sub.checks || {{}};
      const complete = isSetComplete(p.id);

      return `
        <div class="todo-row ${{complete ? 'all-done' : ''}}">
          <div class="todo-meta-line">
            <span class="set-id" onclick="copySetId('${{p.id}}')" title="Click to copy set ID">${{p.id}}</span>
            <span>${{p.image_count}} assets · ${{p.date}}</span>
          </div>

          <div class="todo-title">${{p.title}}</div>

          <div class="platforms-checklist">
            ${{appState.platforms.map(plat => {{
              const item = checks[plat] || {{ submitted: false, date: "" }};
              return `
                <div class="check-pill ${{item.submitted ? 'checked' : ''}}" onclick="togglePlatform('${{p.id}}', '${{plat}}')">
                  <svg class="check-icon" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"></polyline></svg>
                  <span>${{plat}}</span>
                  ${{item.submitted && item.date ? `<span class="sub-date">(${{item.date}})</span>` : ''}}
                </div>
              `;
            }}).join("")}}
          </div>

          <div class="row-footer">
            <button class="row-btn" onclick="toggleNotes('${{p.id}}')">${{sub.notes ? 'Edit note' : '+ Add note'}}</button>
            <button class="row-btn" style="color: var(--text-dim);" onmouseover="this.style.color='#ef4444'" onmouseout="this.style.color='var(--text-dim)'" onclick="deleteProject('${{p.id}}')" title="Remove from checklist">Delete</button>
          </div>

          <div class="row-notes ${{sub.notes ? 'open' : ''}}" id="notes_${{p.id}}">
            <input type="text" class="notes-input" placeholder="Add note (batch number, acceptance, etc)..." value="${{sub.notes || ''}}" onchange="updateNotes('${{p.id}}', this.value)">
          </div>
        </div>
      `;
    }}).join("");
  }}

  function renderApp() {{
    const active = appState.projects.filter(p => !appState.deleted_projects.includes(p.id));
    const total = active.length;
    const completed = active.filter(p => isSetComplete(p.id)).length;
    const pending = total - completed;
    document.getElementById("statusCounter").textContent = `${{total}} sets · ${{pending}} pending · ${{completed}} completed`;
    renderList();
  }}

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

    # If specific set_id provided and not found in scan, add placeholder
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
