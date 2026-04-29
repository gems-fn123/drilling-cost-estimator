#!/usr/bin/env python3
"""Build field-separated interactive WBS trees from dashboard structured cost history."""

from __future__ import annotations

import csv
import html
import json
import re
from datetime import datetime, timezone
from itertools import count
from pathlib import Path
from typing import Iterable, List

from src.io.build_canonical_mappings import extract_full_table, read_xlsx

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"

UNIT_PRICE_HISTORY_MART = PROCESSED / "unit_price_history_mart.csv"
WBS_TREE_COMBINED_JSON = PROCESSED / "wbs_tree_interactive.json"
WBS_TREE_DARAJAT_JSON = PROCESSED / "wbs_tree_field_darajat.json"
WBS_TREE_SALAK_JSON = PROCESSED / "wbs_tree_field_salak.json"
WBS_TREE_WW_JSON = PROCESSED / "wbs_tree_field_wayang_windu.json"
WBS_TREE_HTML = REPORTS / "wbs_tree_interactive.html"
WBS_TREE_REPORT = REPORTS / "wbs_tree_diagram_report.md"

VALID_FIELDS = {"DARAJAT", "SALAK", "WAYANG_WINDU"}


def read_csv(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _safe_float(value: str) -> float:
    text = (value or "0").replace(",", "").strip()
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _format_usd_compact(value: float) -> str:
    abs_value = abs(value)
    sign = "-" if value < 0 else ""
    if abs_value >= 1_000_000_000:
        return f"{sign}{abs_value / 1_000_000_000:.2f}B"
    if abs_value >= 1_000_000:
        return f"{sign}{abs_value / 1_000_000:.2f}M"
    if abs_value >= 1_000:
        return f"{sign}{abs_value / 1_000:.2f}K"
    return f"{sign}{abs_value:,.2f}"


def _percentile(values: Iterable[float], pct: float) -> float:
    arr = sorted(values)
    if not arr:
        return 0.0
    if len(arr) == 1:
        return arr[0]
    idx = (len(arr) - 1) * pct
    lo = int(idx)
    hi = min(lo + 1, len(arr) - 1)
    frac = idx - lo
    return arr[lo] * (1 - frac) + arr[hi] * frac


def _normalize_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").strip().lower())


def _field_from_asset(asset: str) -> str:
    token = _normalize_token(asset)
    if token in {"drj", "darajat"}:
        return "DARAJAT"
    if token in {"slk", "salak"}:
        return "SALAK"
    if token in {"ww", "wayangwindu"}:
        return "WAYANG_WINDU"
    if token in {"wayang", "windu"}:
        return "WAYANG_WINDU"
    return ""


def _record_value(record: dict, *candidates: str) -> str:
    normalized = {_normalize_token(str(key)): str(value).strip() for key, value in record.items()}
    for candidate in candidates:
        found = normalized.get(_normalize_token(candidate))
        if found:
            return found
    return ""


def _build_node(*, field: str, level: int, wbs_id: str, wbs_label: str) -> dict:
    return {
        "field": field,
        "level": level,
        "wbs_id": wbs_id,
        "wbs_label": wbs_label,
        "children": {},
        "_values": [],
        "_campaigns": set(),
        "_source_row_ids": set(),
        "_source_workbooks": set(),
    }


def _display_label(node: dict) -> str:
    wbs_id = (node.get("wbs_id") or "").strip()
    wbs_label = (node.get("wbs_label") or "").strip()
    if wbs_id and wbs_label and wbs_id != wbs_label:
        return f"{wbs_id} - {wbs_label}"
    if wbs_id:
        return wbs_id
    if wbs_label:
        return wbs_label
    return "UNSPECIFIED"


def _node_summary_text(node: dict) -> str:
    return (
        f"{_display_label(node)}\n"
        f"sum {_format_usd_compact(float(node.get('sum_usd', 0.0)))} | "
        f"spr {_format_usd_compact(float(node.get('spread_usd', 0.0)))}"
    )


def _mermaid_label(text: str) -> str:
    return "<br/>".join(html.escape(line, quote=True) for line in text.splitlines())


def _overview_label(node: dict) -> str:
    title = (node.get("node_label") or "").strip()
    if not title:
        title = "UNSPECIFIED"
    return (
        f"{title}\n"
        f"sum {_format_usd_compact(float(node.get('sum_usd', 0.0)))} | "
        f"spr {_format_usd_compact(float(node.get('spread_usd', 0.0)))}"
    )


def _overview_tree(node: dict, *, max_children: int = 4, max_depth: int = 3) -> dict:
    summary = {
        "field": node.get("field", ""),
        "level": node.get("level", 0),
        "wbs_id": node.get("wbs_id", ""),
        "wbs_label": node.get("wbs_label", ""),
        "node_label": node.get("node_label", ""),
        "sum_usd": node.get("sum_usd", 0.0),
        "spread_usd": node.get("spread_usd", 0.0),
        "sample_row_count": node.get("sample_row_count", 0),
        "children": [],
    }

    if max_depth <= 0:
        return summary

    children = sorted(node.get("children", []), key=lambda child: float(child.get("sum_usd", 0.0)), reverse=True)
    visible_children = children[:max_children]
    hidden_children = children[max_children:]

    for child in visible_children:
        summary["children"].append(_overview_tree(child, max_children=max_children, max_depth=max_depth - 1))

    if hidden_children:
        hidden_sum = sum(float(child.get("sum_usd", 0.0)) for child in hidden_children)
        hidden_rows = sum(int(child.get("sample_row_count", 0)) for child in hidden_children)
        summary["children"].append(
            {
                "field": node.get("field", ""),
                "level": node.get("level", 0) + 1,
                "wbs_id": "OTHER",
                "wbs_label": f"+{len(hidden_children)} more",
                "node_label": f"+{len(hidden_children)} more",
                "sum_usd": hidden_sum,
                "spread_usd": 0.0,
                "sample_row_count": hidden_rows,
                "children": [],
            }
        )

    return summary


def _field_summary_text(tree: dict) -> str:
    return (
        f"r={int(tree.get('sample_row_count', 0))} | c={int(tree.get('campaign_count', 0))} | "
        f"sum={_format_usd_compact(float(tree.get('sum_usd', 0.0)))} | "
        f"spr={_format_usd_compact(float(tree.get('spread_usd', 0.0)))}"
    )


def _build_mermaid_diagram(field: str, root: dict) -> str:
    lines = [
        "%%{init: {\"theme\": \"base\", \"securityLevel\": \"loose\", \"flowchart\": {\"curve\": \"basis\", \"nodeSpacing\": 24, \"rankSpacing\": 36, \"htmlLabels\": true}} }%%",
        "flowchart LR",
        "classDef root fill:#0f172a,color:#ffffff,stroke:#0f172a,stroke-width:1.5px;",
        "classDef internal fill:#f8fafc,color:#0f172a,stroke:#94a3b8,stroke-width:1px;",
        "classDef leaf fill:#ecfeff,color:#0f172a,stroke:#06b6d4,stroke-width:1px;",
    ]
    node_ids = count(1)

    def walk(node: dict, parent_id: str | None = None, depth: int = 0) -> None:
        node_id = f"{field.lower()}_{next(node_ids)}"
        label = _mermaid_label(_overview_label(node))
        class_name = "root" if depth == 0 else "leaf" if not node.get("children") else "internal"
        lines.append(f'  {node_id}["{label}"]:::{class_name}')
        if parent_id:
            lines.append(f"  {parent_id} --> {node_id}")
        for child in node.get("children", []):
            walk(child, node_id, depth + 1)

    walk(_overview_tree(root))
    return "\n".join(lines)


def _iter_path(row: dict) -> list[tuple[int, str, str]]:
    return [
        (1, (row.get("l1_id") or "").strip(), (row.get("l1_desc") or "").strip()),
        (2, (row.get("l2_id") or "").strip(), (row.get("l2_desc") or "").strip()),
        (3, (row.get("l3_id") or "").strip(), (row.get("l3_desc") or "").strip()),
        (4, (row.get("l4_id") or "").strip(), (row.get("l4_desc") or "").strip()),
        (5, (row.get("l5_id") or "").strip(), (row.get("l5_desc") or "").strip()),
    ]


def _unit_price_history_rows_to_tree_rows(rows: List[dict]) -> List[dict]:
    filtered: List[dict] = []
    for row in rows:
        field = (row.get("field") or "").strip().upper()
        if field not in VALID_FIELDS:
            continue

        campaign_canonical = (row.get("campaign_canonical") or "").strip()
        campaign_raw = (row.get("campaign_raw") or "").strip()
        campaign_label = campaign_canonical or campaign_raw or "UNSPECIFIED_CAMPAIGN"

        l2 = (row.get("level_2") or "").strip()
        l3 = (row.get("level_3") or "").strip()
        l4 = (row.get("level_4") or "").strip()
        l5 = (row.get("level_5") or "").strip()
        if not all([campaign_label, l2, l3, l4, l5]):
            continue

        actual = _safe_float(row.get("actual_cost_usd", "0"))
        source_row_id = "|".join(
            part
            for part in [
                (row.get("source_workbook") or "").strip(),
                (row.get("source_sheet") or "").strip(),
                (row.get("source_row_key") or "").strip(),
            ]
            if part
        )

        filtered.append(
            {
                "field": field,
                "campaign_canonical": campaign_label,
                "source_row_id": source_row_id,
                "source_workbook": (row.get("source_workbook") or "").strip(),
                "source_sheet": (row.get("source_sheet") or "").strip(),
                "l1_id": campaign_label,
                "l1_desc": campaign_label,
                "l2_id": l2,
                "l2_desc": l2,
                "l3_id": l3,
                "l3_desc": l3,
                "l4_id": l4,
                "l4_desc": l4,
                "l5_id": l5,
                "l5_desc": l5,
                "actual_usd": f"{actual:.6f}",
            }
        )
    return filtered


def _excel_records_to_tree_rows(records: List[dict], source_file: str, source_sheet: str) -> List[dict]:
    rows: List[dict] = []
    for idx, record in enumerate(records, start=1):
        field = _field_from_asset(_record_value(record, "Asset"))
        if field not in VALID_FIELDS:
            continue

        legacy_l1 = _record_value(record, "L1")
        structured_l2 = _record_value(record, "Level 2")
        is_legacy_schema = bool(legacy_l1)

        if is_legacy_schema:
            l1_id = legacy_l1
            l2_id = _record_value(record, "L2")
            l3_id = _record_value(record, "L3")
            l4_id = _record_value(record, "L4")
            l5_id = _record_value(record, "L5")
            l5_desc = _record_value(record, "Description", "L5 Description", "L5") or l5_id
            actual = _safe_float(_record_value(record, "ACTUAL, USD", "ACTUAL USD", "Actual, USD"))
            campaign_name = _record_value(record, "Campaign", "Drilling Campaign")
        else:
            campaign_name = _record_value(record, "Campaign", "Drilling Campaign")
            l1_id = campaign_name or "UNSPECIFIED_CAMPAIGN"
            l2_id = structured_l2
            l3_id = _record_value(record, "Level 3")
            l4_id = _record_value(record, "Level 4")
            l5_id = _record_value(record, "Level 5")
            l5_desc = l5_id
            actual = _safe_float(_record_value(record, "Actual Cost USD", "ACTUAL COST USD"))

        if not all([l1_id, l2_id, l3_id, l4_id, l5_id]):
            continue

        rows.append(
            {
                "field": field,
                "campaign_canonical": campaign_name or "UNSPECIFIED_CAMPAIGN",
                "source_row_id": f"{source_file}|{source_sheet}|{idx}",
                "source_workbook": source_file,
                "source_sheet": source_sheet,
                "l1_id": l1_id,
                "l1_desc": l1_id,
                "l2_id": l2_id,
                "l2_desc": l2_id,
                "l3_id": l3_id,
                "l3_desc": l3_id,
                "l4_id": l4_id,
                "l4_desc": l4_id,
                "l5_id": l5_id,
                "l5_desc": l5_desc,
                "actual_usd": f"{actual:.6f}",
            }
        )
    return rows


def _add_row_to_tree(root: dict, row: dict) -> None:
    value = _safe_float(row.get("actual_usd", "0"))
    campaign = (row.get("campaign_canonical") or "").strip()
    source_row_id = (row.get("source_row_id") or "").strip()
    source_workbook = (row.get("source_workbook") or "").strip()

    root["_values"].append(value)
    if campaign:
        root["_campaigns"].add(campaign)
    if source_row_id:
        root["_source_row_ids"].add(source_row_id)
    if source_workbook:
        root["_source_workbooks"].add(source_workbook)

    cursor = root
    for level, wbs_id, wbs_label in _iter_path(row):
        key = f"L{level}:{wbs_id}"
        if key not in cursor["children"]:
            cursor["children"][key] = _build_node(
                field=row["field"],
                level=level,
                wbs_id=wbs_id,
                wbs_label=wbs_label,
            )
        cursor = cursor["children"][key]
        cursor["_values"].append(value)
        if campaign:
            cursor["_campaigns"].add(campaign)
        if source_row_id:
            cursor["_source_row_ids"].add(source_row_id)
        if source_workbook:
            cursor["_source_workbooks"].add(source_workbook)


def _finalize_node(node: dict) -> dict:
    values = sorted(node.pop("_values"))
    campaigns = sorted(node.pop("_campaigns"))
    source_rows = sorted(node.pop("_source_row_ids"))
    source_workbooks = sorted(node.pop("_source_workbooks"))

    sum_usd = sum(values)
    median_usd = _percentile(values, 0.50)
    p10_usd = _percentile(values, 0.10)
    p90_usd = _percentile(values, 0.90)
    spread_usd = max(0.0, p90_usd - p10_usd)
    spread_pct = (spread_usd / median_usd * 100.0) if median_usd else 0.0

    node["node_label"] = _display_label(node)
    node["sample_row_count"] = len(values)
    node["campaign_count"] = len(campaigns)
    node["campaigns"] = campaigns
    node["sum_usd"] = round(sum_usd, 6)
    node["median_usd"] = round(median_usd, 6)
    node["p10_usd"] = round(p10_usd, 6)
    node["p90_usd"] = round(p90_usd, 6)
    node["spread_usd"] = round(spread_usd, 6)
    node["spread_pct"] = round(spread_pct, 4)
    node["source_row_count"] = len(source_rows)
    node["source_row_ids_sample"] = source_rows[:30]
    node["source_workbooks"] = source_workbooks

    children = [
        _finalize_node(child)
        for _, child in sorted(
            node["children"].items(),
            key=lambda item: (
                item[1].get("level", 99),
                item[1].get("wbs_id", ""),
                item[1].get("wbs_label", ""),
            ),
        )
    ]
    node["children"] = children
    return node


def _build_field_tree(rows: List[dict], field: str) -> dict:
    field_rows = [row for row in rows if row["field"] == field]
    root = _build_node(field=field, level=0, wbs_id=f"{field}_ROOT", wbs_label=f"{field} WBS Tree")

    for row in field_rows:
        _add_row_to_tree(root, row)

    return _finalize_node(root)


def _count_nodes(node: dict) -> int:
    return 1 + sum(_count_nodes(child) for child in node.get("children", []))


def _count_leaves(node: dict) -> int:
    children = node.get("children", [])
    if not children:
        return 1
    return sum(_count_leaves(child) for child in children)


def _build_payload_from_rows(rows: List[dict], source_contract: dict) -> dict:
    fields: dict = {}
    for field in sorted(VALID_FIELDS):
        tree = _build_field_tree(rows, field)
        tree["node_count"] = _count_nodes(tree) - 1
        tree["leaf_count"] = _count_leaves(tree) if tree.get("children") else 0
        fields[field] = tree

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_contract": source_contract,
        "fields": fields,
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def render_wbs_tree_html(payload: dict) -> str:
    sections: list[dict[str, str]] = []
    for field in sorted(payload.get("fields", {}).keys()):
        tree = payload["fields"][field]
        sections.append(
            {
                "field": field,
                "summary": _field_summary_text(tree),
                "diagram": _build_mermaid_diagram(field, tree),
            }
        )

    sections_json = json.dumps(sections, ensure_ascii=False).replace("</", "<\\/")
    generated_at = html.escape(str(payload.get("generated_at_utc", "n/a")), quote=True)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Interactive WBS Tree</title>
  <style>
    :root {{ color-scheme: light; }}
    body {{ font-family: Inter, Arial, sans-serif; margin: 20px; color: #111827; background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%); }}
    h1 {{ margin: 0 0 0.35rem 0; font-size: 28px; letter-spacing: -0.02em; }}
    .subtitle {{ color: #4b5563; margin: 0 0 14px 0; }}
    .legend {{ background: #ecfeff; border: 1px solid #67e8f9; border-radius: 10px; padding: 10px 12px; margin: 12px 0 18px 0; color: #155e75; }}
    .meta {{ color: #6b7280; font-size: 12px; margin-top: 4px; }}
    #trees {{ display: grid; gap: 18px; }}
    .field-card {{ border: 1px solid #d1d5db; border-radius: 14px; padding: 14px; background: rgba(255, 255, 255, 0.92); box-shadow: 0 8px 30px rgba(15, 23, 42, 0.05); }}
    .field-header {{ display: flex; flex-wrap: wrap; gap: 8px 12px; align-items: baseline; margin-bottom: 10px; }}
    .field-title {{ margin: 0; font-size: 20px; letter-spacing: 0.01em; }}
    .field-summary {{ margin: 0; color: #374151; font-size: 13px; }}
    .diagram-wrap {{ overflow-x: auto; overflow-y: hidden; border-radius: 12px; background: #fff; border: 1px solid #e5e7eb; padding: 8px; }}
    .diagram-wrap .mermaid {{ min-width: 100%; }}
  </style>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
</head>
<body>
    <h1>WBS Flowchart</h1>
    <p class="subtitle">Dashboard Structured.Cost rows, split by field.</p>
    <div class="legend">sum = descendant total. spr = P90 - P10.</div>
  <div class="meta">Generated at UTC: {generated_at}</div>
  <div id="trees"></div>
  <script>
    const sections = {sections_json};

    mermaid.initialize({{
      startOnLoad: false,
      theme: 'base',
      securityLevel: 'loose',
      flowchart: {{
        curve: 'basis',
        nodeSpacing: 14,
        rankSpacing: 18,
        htmlLabels: true,
      }},
    }});

    const treesEl = document.getElementById('trees');
    sections.forEach((item) => {{
      const section = document.createElement('section');
      section.className = 'field-card';

      const header = document.createElement('div');
      header.className = 'field-header';

      const title = document.createElement('h2');
      title.className = 'field-title';
      title.textContent = item.field;
      header.appendChild(title);

      const summary = document.createElement('p');
      summary.className = 'field-summary';
      summary.textContent = item.summary;
      header.appendChild(summary);

      const diagramWrap = document.createElement('div');
      diagramWrap.className = 'diagram-wrap';

      const diagram = document.createElement('div');
      diagram.className = 'mermaid';
      diagram.textContent = item.diagram;
      diagramWrap.appendChild(diagram);

      section.appendChild(header);
      section.appendChild(diagramWrap);
      treesEl.appendChild(section);
    }});

    mermaid.run({{ querySelector: '.mermaid' }});
  </script>
</body>
</html>
"""


def _write_html(payload: dict) -> None:
    WBS_TREE_HTML.write_text(render_wbs_tree_html(payload), encoding="utf-8")


def _write_report(payload: dict) -> None:
    lines = [
        "# WBS Tree Diagram Report",
        "",
        f"Generated: {payload['generated_at_utc']}",
        "",
        "## Source Contract",
        "- Source dataset: `data/processed/unit_price_history_mart.csv`",
        "- Included rows: `Structured.Cost` lineage rows with complete campaign + Level 2..5 hierarchy.",
        "- Field handling: DARAJAT, SALAK, and WAYANG_WINDU are built as separate trees.",
        "",
        "## Field Snapshot",
    ]

    for field in sorted(payload["fields"].keys()):
        tree = payload["fields"][field]
        lines.extend(
            [
                f"- **{field}**: node_count={tree['node_count']}, leaf_count={tree['leaf_count']}, "
                f"r={tree['sample_row_count']}, c={tree['campaign_count']}, "
                f"sum={tree['sum_usd']:.2f}, spr={tree['spread_usd']:.2f} ({tree['spread_pct']:.2f}%).",
            ]
        )

    lines.extend(
        [
            "",
            "## Output Artifacts",
            "- `data/processed/wbs_tree_interactive.json`",
            "- `data/processed/wbs_tree_field_darajat.json`",
            "- `data/processed/wbs_tree_field_salak.json`",
            "- `data/processed/wbs_tree_field_wayang_windu.json`",
            "- `reports/wbs_tree_interactive.html`",
        ]
    )

    WBS_TREE_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_wbs_tree_artifacts() -> dict:
    source_rows = read_csv(UNIT_PRICE_HISTORY_MART)
    rows = _unit_price_history_rows_to_tree_rows(source_rows)

    payload = _build_payload_from_rows(
        rows,
        {
            "dataset": UNIT_PRICE_HISTORY_MART.relative_to(ROOT).as_posix(),
            "source_sheet_required": "Structured.Cost",
            "campaign_mapping_required": True,
            "hierarchy_required": "Campaign + Level 2-5 complete",
        },
    )

    _write_json(WBS_TREE_COMBINED_JSON, payload)
    _write_json(
        WBS_TREE_DARAJAT_JSON,
        {"generated_at_utc": payload["generated_at_utc"], "field": "DARAJAT", "tree": payload["fields"]["DARAJAT"]},
    )
    _write_json(
        WBS_TREE_SALAK_JSON,
        {"generated_at_utc": payload["generated_at_utc"], "field": "SALAK", "tree": payload["fields"]["SALAK"]},
    )
    _write_json(
        WBS_TREE_WW_JSON,
        {"generated_at_utc": payload["generated_at_utc"], "field": "WAYANG_WINDU", "tree": payload["fields"]["WAYANG_WINDU"]},
    )
    _write_html(payload)
    _write_report(payload)

    return {
        "source_row_count": len(rows),
        "darajat_row_count": payload["fields"]["DARAJAT"]["sample_row_count"],
        "salak_row_count": payload["fields"]["SALAK"]["sample_row_count"],
        "wayang_windu_row_count": payload["fields"]["WAYANG_WINDU"]["sample_row_count"],
        "combined_json": WBS_TREE_COMBINED_JSON.relative_to(ROOT).as_posix(),
        "darajat_json": WBS_TREE_DARAJAT_JSON.relative_to(ROOT).as_posix(),
        "salak_json": WBS_TREE_SALAK_JSON.relative_to(ROOT).as_posix(),
        "wayang_windu_json": WBS_TREE_WW_JSON.relative_to(ROOT).as_posix(),
        "interactive_html": WBS_TREE_HTML.relative_to(ROOT).as_posix(),
    }


def build_wbs_tree_from_excel_sheet(excel_path: Path, sheet_name: str = "Data.Summary") -> dict:
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    workbook = read_xlsx(excel_path)
    if sheet_name not in workbook:
        available = ", ".join(sorted(workbook.keys()))
        raise ValueError(f"Sheet '{sheet_name}' not found. Available sheets: {available}")

    records = extract_full_table(workbook[sheet_name], ["Asset", "ACTUAL, USD", "L1", "L2", "L3", "L4", "L5"])
    if not records:
        records = extract_full_table(
            workbook[sheet_name],
            ["Asset", "Campaign", "Level 2", "Level 3", "Level 4", "Level 5", "Actual Cost USD"],
        )
    if not records:
        raise ValueError(
            f"No table rows found in sheet '{sheet_name}' with either "
            "legacy columns (Asset, ACTUAL, USD, L1-L5) or dashboard columns "
            "(Asset, Campaign, Level 2-5, Actual Cost USD)."
        )

    rows = _excel_records_to_tree_rows(records, excel_path.name, sheet_name)
    if not rows:
        raise ValueError("No valid field-separated rows found (expected Asset mapping to DARAJAT/SLK and complete L1-L5).")

    return _build_payload_from_rows(
        rows,
        {
            "dataset": str(excel_path),
            "source_sheet_required": sheet_name,
            "campaign_mapping_required": False,
            "hierarchy_required": "L1-L5 complete",
        },
    )


def load_wbs_tree_payload(path: Path = WBS_TREE_COMBINED_JSON) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"WBS tree payload not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    build_wbs_tree_artifacts()
