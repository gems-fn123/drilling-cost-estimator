from __future__ import annotations

import json
from statistics import median
from typing import Sequence

from streamlit_echarts import JsCode


def _number_formatter_js(*, decimals: int = 2, integer: bool = False) -> JsCode:
    if integer:
        return JsCode(
            """
            function(value) {
                const raw = value && typeof value === 'object' && value.value !== undefined ? value.value : value;
                const num = Number(raw);
                if (!Number.isFinite(num)) {
                    return raw ?? '';
                }
                return Math.round(num).toLocaleString();
            }
            """
        )

    return JsCode(
        f"""
        function(value) {{
            const raw = value && typeof value === 'object' && value.value !== undefined ? value.value : value;
            const num = Number(raw);
            if (!Number.isFinite(num)) {{
                return raw ?? '';
            }}
            return num.toLocaleString(undefined, {{
                minimumFractionDigits: 0,
                maximumFractionDigits: {decimals}
            }});
        }}
        """
    )


def _axis_tooltip_formatter_js(*, unit: str = "", integer: bool = False, decimals: int = 2) -> JsCode:
    suffix = f" {unit}".rstrip()
    unit_json = json.dumps(suffix)
    decimals_js = 0 if integer else decimals
    round_js = "Math.round(num).toLocaleString()" if integer else (
        f"num.toLocaleString(undefined, {{ minimumFractionDigits: 0, maximumFractionDigits: {decimals_js} }})"
    )
    return JsCode(
        f"""
        function(params) {{
            if (!params || !params.length) {{
                return '';
            }}
            const lines = [params[0].axisValueLabel || ''];
            params.forEach(function(item) {{
                const num = Number(item.value);
                const formatted = Number.isFinite(num)
                    ? {round_js}
                    : (item.value ?? '');
                lines.push(item.marker + item.seriesName + ': ' + formatted + {unit_json});
            }});
            return lines.join('<br/>');
        }}
        """
    )


def _single_point_tooltip_formatter_js(*, unit: str = "", integer: bool = False, decimals: int = 2) -> JsCode:
    suffix = f" {unit}".rstrip()
    unit_json = json.dumps(suffix)
    decimals_js = 0 if integer else decimals
    round_js = "Math.round(num).toLocaleString()" if integer else (
        f"num.toLocaleString(undefined, {{ minimumFractionDigits: 0, maximumFractionDigits: {decimals_js} }})"
    )
    return JsCode(
        f"""
        function(params) {{
            const num = Number(params.value);
            const formatted = Number.isFinite(num)
                ? {round_js}
                : (params.value ?? '');
            return (params.name || params.seriesName || '') + '<br/>' + params.marker + params.seriesName + ': ' + formatted + {unit_json};
        }}
        """
    )


def build_bar_chart_options(
    title: str,
    categories: Sequence[str],
    values: Sequence[float],
    *,
    series_name: str,
    subtitle: str = "",
    unit: str = "",
    color: str = "#0ea5e9",
    horizontal: bool = True,
    integer_labels: bool = False,
) -> dict:
    value_formatter = _number_formatter_js(decimals=2, integer=integer_labels)
    tooltip_formatter = _axis_tooltip_formatter_js(unit=unit, integer=integer_labels, decimals=2)
    if horizontal:
        x_axis = {
            "type": "value",
            "name": unit,
            "min": 0,
            "axisLabel": {"formatter": value_formatter},
        }
        y_axis = {"type": "category", "data": list(categories), "axisLabel": {"interval": 0}}
    else:
        x_axis = {"type": "category", "data": list(categories), "axisLabel": {"interval": 0, "rotate": 18}}
        y_axis = {
            "type": "value",
            "name": unit,
            "min": 0,
            "axisLabel": {"formatter": value_formatter},
        }

    return {
        "title": {"text": title, "subtext": subtitle, "left": "center"},
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}, "formatter": tooltip_formatter},
        "grid": {"left": "6%", "right": "4%", "bottom": "4%", "top": "16%", "containLabel": True},
        "xAxis": x_axis,
        "yAxis": y_axis,
        "series": [
            {
                "name": series_name,
                "type": "bar",
                "data": list(values),
                "itemStyle": {"color": color},
                "label": {
                    "show": True,
                    "position": "right" if horizontal else "top",
                    "formatter": value_formatter,
                },
            }
        ],
    }


def build_stacked_bar_chart_options(
    title: str,
    categories: Sequence[str],
    series_rows: Sequence[dict[str, object]],
    *,
    subtitle: str = "",
    unit: str = "",
    horizontal: bool = False,
    integer_labels: bool = False,
    show_labels: bool = True,
) -> dict:
    value_formatter = _number_formatter_js(decimals=2, integer=integer_labels)
    tooltip_formatter = _axis_tooltip_formatter_js(unit=unit, integer=integer_labels, decimals=2)
    label_formatter = JsCode(
        f"""
        function(params) {{
            const num = Number(params.value);
            if (!Number.isFinite(num) || Math.abs(num) < 1e-9) {{
                return '';
            }}
            return num.toLocaleString(undefined, {{
                minimumFractionDigits: 0,
                maximumFractionDigits: {0 if integer_labels else 2}
            }});
        }}
        """
    )

    if horizontal:
        x_axis = {
            "type": "value",
            "name": unit,
            "min": 0,
            "axisLabel": {"formatter": value_formatter},
        }
        y_axis = {"type": "category", "data": list(categories), "axisLabel": {"interval": 0}}
    else:
        x_axis = {"type": "category", "data": list(categories), "axisLabel": {"interval": 0}}
        y_axis = {
            "type": "value",
            "name": unit,
            "min": 0,
            "axisLabel": {"formatter": value_formatter},
        }

    series = []
    for row in series_rows:
        series.append(
            {
                "name": str(row.get("name", "")),
                "type": "bar",
                "stack": "total",
                "data": list(row.get("data", [])),
                "itemStyle": {"color": str(row.get("color", "#0ea5e9"))},
                "label": {
                    "show": show_labels,
                    "position": "inside" if horizontal else "top",
                    "formatter": label_formatter,
                },
                "emphasis": {"focus": "series"},
            }
        )

    return {
        "title": {"text": title, "subtext": subtitle, "left": "center"},
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}, "formatter": tooltip_formatter},
        "legend": {"top": "9%", "type": "scroll"},
        "grid": {"left": "6%", "right": "4%", "bottom": "4%", "top": "22%", "containLabel": True},
        "xAxis": x_axis,
        "yAxis": y_axis,
        "series": series,
    }


def build_dual_axis_line_chart_options(
    title: str,
    categories: Sequence[str],
    left_series_name: str,
    left_values: Sequence[float | None],
    right_series_name: str,
    right_values: Sequence[float | None],
    *,
    subtitle: str = "",
    annotation: str = "",
    left_unit: str = "",
    right_unit: str = "",
    left_color: str = "#0f766e",
    right_color: str = "#2563eb",
) -> dict:
    left_formatter = _number_formatter_js(decimals=2, integer=False)
    right_formatter = _number_formatter_js(decimals=2, integer=False)
    return {
        "title": {"text": title, "subtext": subtitle, "left": "center"},
        "graphic": (
            [
                {
                    "type": "text",
                    "right": 10,
                    "top": 10,
                    "z": 100,
                    "style": {
                        "text": annotation,
                        "fill": "#475569",
                        "font": "12px sans-serif",
                        "textAlign": "right",
                    },
                }
            ]
            if annotation
            else []
        ),
        "tooltip": {
            "trigger": "axis",
            "formatter": JsCode(
                f"""
                function(params) {{
                    if (!params || !params.length) {{
                        return '';
                    }}
                    const lines = [params[0].axisValueLabel || ''];
                    params.forEach(function(item) {{
                        const axisUnit = item.seriesName === {json.dumps(left_series_name)} ? {json.dumps(left_unit)} : {json.dumps(right_unit)};
                        const num = Number(item.value);
                        const formatted = Number.isFinite(num)
                            ? num.toLocaleString(undefined, {{ minimumFractionDigits: 0, maximumFractionDigits: 2 }})
                            : 'n/a';
                        lines.push(item.marker + item.seriesName + ': ' + formatted + (axisUnit ? ' ' + axisUnit : ''));
                    }});
                    return lines.join('<br/>');
                }}
                """
            ),
        },
        "legend": {"top": "10%", "type": "plain"},
        "grid": {"left": "7%", "right": "7%", "bottom": "5%", "top": "22%", "containLabel": True},
        "xAxis": {"type": "category", "data": list(categories), "boundaryGap": False},
        "yAxis": [
            {"type": "value", "name": left_unit, "axisLabel": {"formatter": left_formatter}, "scale": True},
            {"type": "value", "name": right_unit, "axisLabel": {"formatter": right_formatter}, "scale": True},
        ],
        "series": [
            {
                "name": left_series_name,
                "type": "line",
                "data": list(left_values),
                "yAxisIndex": 0,
                "showSymbol": True,
                "symbol": "circle",
                "symbolSize": 7,
                "connectNulls": False,
                "smooth": False,
                "lineStyle": {"width": 3, "color": left_color},
                "itemStyle": {"color": left_color},
            },
            {
                "name": right_series_name,
                "type": "line",
                "data": list(right_values),
                "yAxisIndex": 1,
                "showSymbol": True,
                "symbol": "diamond",
                "symbolSize": 7,
                "connectNulls": False,
                "smooth": False,
                "lineStyle": {"width": 3, "color": right_color, "type": "dashed"},
                "itemStyle": {"color": right_color},
            },
        ],
    }


def build_candlestick_chart_options(
    title: str,
    categories: Sequence[str],
    candles: Sequence[Sequence[float]],
    *,
    subtitle: str = "",
    unit: str = "",
    color_up: str = "#0f766e",
    color_down: str = "#0ea5e9",
) -> dict:
    return {
        "title": {"text": title, "subtext": subtitle, "left": "center"},
        "tooltip": {"trigger": "item"},
        "grid": {"left": "4%", "right": "4%", "bottom": "3%", "containLabel": True},
        "xAxis": {"type": "category", "data": list(categories), "axisLabel": {"interval": 0, "rotate": 18}},
        "yAxis": {"type": "value", "scale": True, "name": unit},
        "series": [
            {
                "name": title,
                "type": "candlestick",
                "data": [list(candle) for candle in candles],
                "itemStyle": {
                    "color": color_up,
                    "color0": color_down,
                    "borderColor": color_up,
                    "borderColor0": color_down,
                },
            }
        ],
    }


def _distribution_stats(values: Sequence[float]) -> dict[str, float]:
    ordered = sorted(float(value) for value in values)
    count = len(ordered)
    if count == 0:
        return {}

    def _quantile(q: float) -> float:
        if count == 1:
            return ordered[0]
        position = (count - 1) * q
        lower = int(position)
        upper = min(lower + 1, count - 1)
        weight = position - lower
        return ordered[lower] * (1 - weight) + ordered[upper] * weight

    return {
        "count": float(count),
        "min": ordered[0],
        "q1": _quantile(0.25),
        "median": float(median(ordered)),
        "q3": _quantile(0.75),
        "max": ordered[-1],
        "mean": sum(ordered) / count,
    }


def build_distribution_boxplot_options(
    title: str,
    groups: Sequence[dict[str, object]],
    *,
    subtitle: str = "",
    unit: str = "",
    fill_color: str = "#0f766e",
    stroke_color: str = "#0f766e",
) -> dict:
    labels: list[str] = []
    box_rows: list[list[float]] = []
    tooltip_rows: list[dict[str, object]] = []
    for index, group in enumerate(groups):
        label = str(group.get("label", f"group-{index + 1}"))
        values = [float(value) for value in group.get("values", []) if value is not None]
        if not values:
            continue
        stats = _distribution_stats(values)
        labels.append(label)
        box_rows.append([stats["min"], stats["q1"], stats["median"], stats["q3"], stats["max"]])
        tooltip_rows.append(
            {
                "label": label,
                "sample_count": int(stats["count"]),
                "min": stats["min"],
                "q1": stats["q1"],
                "median": stats["median"],
                "q3": stats["q3"],
                "max": stats["max"],
                "mean": stats["mean"],
            }
        )

    tooltip_unit = f" {unit}".rstrip()
    unit_json = json.dumps(tooltip_unit)

    return {
        "title": {"text": title, "subtext": subtitle, "left": "center"},
        "tooltip": {
            "trigger": "item",
            "formatter": JsCode(
                f"""
                function(params) {{
                    const d = (params.dataIndex >= 0 && params.dataIndex < {json.dumps(tooltip_rows)}.length)
                        ? {json.dumps(tooltip_rows)}[params.dataIndex]
                        : {{}};
                    const fmt = function(value) {{
                        const num = Number(value);
                        return Number.isFinite(num)
                            ? num.toLocaleString(undefined, {{ minimumFractionDigits: 0, maximumFractionDigits: 2 }})
                            : 'n/a';
                    }};
                    return [
                        '<strong>' + (d.label || params.seriesName || '') + '</strong>',
                        'Samples: ' + (d.sample_count ?? 'n/a'),
                        'Min: ' + fmt(d.min) + {unit_json},
                        'Q1: ' + fmt(d.q1) + {unit_json},
                        'Median: ' + fmt(d.median) + {unit_json},
                        'Q3: ' + fmt(d.q3) + {unit_json},
                        'Max: ' + fmt(d.max) + {unit_json}
                    ].join('<br/>');
                }}
                """
            ),
        },
        "grid": {"left": "8%", "right": "4%", "bottom": "6%", "top": "18%", "containLabel": True},
        "xAxis": {"type": "category", "data": labels, "axisLabel": {"interval": 0}},
        "yAxis": {
            "type": "value",
            "name": unit,
            "scale": True,
            "axisLabel": {"formatter": _number_formatter_js(decimals=2, integer=False)},
        },
        "series": [
            {
                "name": title,
                "type": "boxplot",
                "data": box_rows,
                "itemStyle": {
                    "color": fill_color,
                    "borderColor": stroke_color,
                    "borderWidth": 2,
                },
            }
        ],
    }


def build_line_chart_options(
    title: str,
    categories: Sequence[str],
    series_rows: Sequence[dict[str, object]],
    *,
    subtitle: str = "",
    unit: str = "Pearson r",
    y_min: float = -1.0,
    y_max: float = 1.0,
) -> dict:
    palette = ["#0f766e", "#2563eb", "#7c3aed", "#ea580c", "#dc2626", "#16a34a"]
    series = []
    for idx, row in enumerate(series_rows):
        color = str(row.get("color") or palette[idx % len(palette)])
        series.append(
            {
                "name": str(row.get("name", f"series-{idx + 1}")),
                "type": "line",
                "data": list(row.get("data", [])),
                "showSymbol": True,
                "symbol": "circle",
                "symbolSize": 6,
                "smooth": True,
                "connectNulls": False,
                "lineStyle": {"width": 2, "color": color},
                "itemStyle": {"color": color},
            }
        )

    return {
        "title": {"text": title, "subtext": subtitle, "left": "center"},
        "tooltip": {"trigger": "axis"},
        "legend": {"top": "16%", "type": "scroll"},
        "grid": {"left": "4%", "right": "4%", "top": "26%", "bottom": "3%", "containLabel": True},
        "xAxis": {"type": "category", "data": list(categories), "boundaryGap": False},
        "yAxis": {"type": "value", "name": unit, "min": y_min, "max": y_max},
        "series": series,
    }


def build_heatmap_chart_options(
    title: str,
    x_labels: Sequence[str],
    y_labels: Sequence[str],
    points: Sequence[Sequence[float]],
    *,
    subtitle: str = "",
    value_label: str = "Pearson r",
    min_value: float = -1.0,
    max_value: float = 1.0,
) -> dict:
    return {
        "title": {"text": title, "subtext": subtitle, "left": "center"},
        "tooltip": {
            "position": "top",
            "formatter": JsCode(
                f"""
                function(params) {{
                    const value = Array.isArray(params.value) ? params.value[2] : params.value;
                    const formatted = Number(value).toLocaleString(undefined, {{ minimumFractionDigits: 0, maximumFractionDigits: 3 }});
                    return params.marker + params.name + '<br/>{value_label}: ' + formatted;
                }}
                """
            ),
        },
        "grid": {"height": "68%", "top": "14%", "left": "8%", "right": "4%", "containLabel": True},
        "xAxis": {
            "type": "category",
            "data": list(x_labels),
            "splitArea": {"show": True},
            "axisLabel": {"interval": 0, "rotate": 16},
        },
        "yAxis": {
            "type": "category",
            "data": list(y_labels),
            "splitArea": {"show": True},
            "axisLabel": {"interval": 0},
        },
        "visualMap": {
            "min": min_value,
            "max": max_value,
            "calculable": True,
            "orient": "horizontal",
            "left": "center",
            "bottom": "0%",
            "inRange": {"color": ["#ef4444", "#f8fafc", "#2563eb"]},
        },
        "series": [
            {
                "name": value_label,
                "type": "heatmap",
                "data": [list(point) for point in points],
                "label": {"show": False},
                "emphasis": {"itemStyle": {"shadowBlur": 10, "shadowColor": "rgba(0,0,0,0.3)"}},
            }
        ],
    }
