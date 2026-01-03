"""
Vega-Lite chart specification generator.

This module provides functions to generate Vega-Lite JSON specifications
for different chart types with beautiful defaults.
"""
from typing import Dict, Any, Optional, List

# Colorblind-safe color palettes
COLORBLIND_SAFE_PALETTES = {
    'categorical': [
        '#1f77b4',  # Blue
        '#ff7f0e',  # Orange
        '#2ca02c',  # Green
        '#d62728',  # Red
        '#9467bd',  # Purple
        '#8c564b',  # Brown
        '#e377c2',  # Pink
        '#7f7f7f',  # Gray
        '#bcbd22',  # Yellow-green
        '#17becf'   # Cyan
    ],
    'sequential': [
        '#f7fbff',
        '#deebf7',
        '#c6dbef',
        '#9ecae1',
        '#6baed6',
        '#4292c6',
        '#2171b5',
        '#08519c',
        '#08306b'
    ],
    'diverging': [
        '#67001f',
        '#b2182b',
        '#d6604d',
        '#f4a582',
        '#fddbc7',
        '#f7f7f7',
        '#d1e5f0',
        '#92c5de',
        '#4393c3',
        '#2166ac',
        '#053061'
    ]
}


def sanitize_field_name(field: str) -> str:
    """
    Sanitize field names for Vega-Lite compatibility.
    
    Vega-Lite uses a path accessor syntax that breaks on:
    - Newlines and carriage returns
    - Apostrophes (')
    - Backslashes (\\)
    - Dots (.) - treated as nested path
    
    We escape/remove these characters to prevent parsing errors.
    """
    if not field:
        return field
    
    # Remove newlines and carriage returns (these break Vega parsing completely)
    result = field.replace('\n', ' ').replace('\r', ' ')
    # Collapse multiple spaces
    result = ' '.join(result.split())
    # Escape backslashes first (must be done first)
    result = result.replace('\\', '\\\\')
    # Escape apostrophes/single quotes
    result = result.replace("'", "\\'")
    
    return result

def generate_vega_spec(
    chart_type: str,
    x: str,
    title: str,
    y: Optional[str] = None,
    x_type: str = "nominal",
    y_type: str = "quantitative",
    color: Optional[str] = None,
    y_aggregate: Optional[str] = None  # sum, mean, count, min, max
) -> Dict[str, Any]:
    """
    Generate a Vega-Lite specification for a chart.
    
    Args:
        chart_type: Type of chart ('line', 'bar', 'scatter', 'histogram', 'circle')
        x: Field name for x-axis
        title: Chart title
        y: Optional field name for y-axis
        x_type: Type of x-axis data ('nominal', 'quantitative', 'temporal', 'ordinal')
        y_type: Type of y-axis data ('nominal', 'quantitative', 'temporal', 'ordinal')
        color: Optional field name for color encoding
        y_aggregate: Optional aggregation for y-axis ('sum', 'mean', 'count', 'min', 'max')
        
    Returns:
        Dictionary containing the Vega-Lite specification
    """
    
    # Sanitize field names for Vega-Lite compatibility (handles apostrophes, etc.)
    x = sanitize_field_name(x)
    if y:
        y = sanitize_field_name(y)
    if color:
        color = sanitize_field_name(color)
    
    
    # Truncate very long titles to prevent overflow
    display_title = title if len(title) <= 60 else title[:57] + "..."
    
    # Base spec with "Premium" defaults
    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
        "title": {
            "text": display_title,
            "fontSize": 18,
            "anchor": "start",
            "font": "Inter, sans-serif",
            "fontWeight": 600,
            "color": "#111827",
            "limit": 500  # Max width in pixels before truncation
        },
        "width": "container",
        "height": 400,
        "config": {
            "font": "Inter, sans-serif",
            "axis": {
                "labelFontSize": 11,
                "titleFontSize": 13,
                "titleFontWeight": 500,
                "titleColor": "#6b7280",
                "labelColor": "#6b7280",
                "grid": True,
                "gridColor": "#f3f4f6",
                "gridDash": [4, 4],
                "labelLimit": 120,  # Truncate long labels
                "titleLimit": 200,  # Truncate long titles
                "labelOverlap": "parity",  # Hide overlapping labels
                "domain": False,
                "tickColor": "#e5e7eb"
            },
            "view": {
                "stroke": "transparent"
            }
        },
        "data": {"name": "table"}
    }
    
    # Layered specification for premium feel
    if chart_type == "area":
        # Handle Count Aggregation (no explicit Y field)
        y_field = y if y else "count"
        y_title = "Count" if not y else y
        y_def = {"aggregate": "count", "title": "Count"} if not y else {"field": y, "type": y_type}
        
        spec["layer"] = [
            # Gradient Area
            {
                "mark": {
                    "type": "area",
                    "line": {"color": "#2563eb", "strokeWidth": 3},
                    "color": {
                        "x1": 1,
                        "y1": 1,
                        "x2": 1,
                        "y2": 0,
                        "gradient": "linear",
                        "stops": [
                            {"offset": 0, "color": "white"},
                            {"offset": 1, "color": "#2563eb"}
                        ]
                    },
                    "opacity": 0.2
                },
                "encoding": {
                    "x": {"field": x, "type": x_type, "axis": {"labelAngle": 0, "grid": False}},
                    "y": y_def
                }
            },
            # Interactive Points on Hover (Only if not using count agg, as points are messy for count over time usually)
            # Actually, points are fine for count over time if aggregated.
            {
                "mark": {"type": "circle", "size": 60, "color": "#2563eb", "filled": True},
                "encoding": {
                    "x": {"field": x, "type": x_type},
                    "y": y_def,
                    "opacity": {
                        "condition": {"param": "hover", "value": 1},
                        "value": 0
                    },
                    "tooltip": [
                        {"field": x, "type": x_type},
                        {"field": y_field, "type": "quantitative", "format": ",", "title": y_title}
                    ]
                }
            },
            # Vertical Crosshair Rule
            {
                "mark": {"type": "rule", "color": "#9ca3af", "strokeWidth": 1, "strokeDash": [4, 4]},
                "encoding": {
                    "x": {"field": x, "type": x_type},
                    "y": y_def,
                    "opacity": {
                        "condition": {"param": "hover", "value": 1},
                        "value": 0
                    }
                }
            },
            # Invisible Selector for Interactivity
            {
                "mark": {"type": "bar", "opacity": 0}, 
                "encoding": {
                    "x": {"field": x, "type": x_type},
                     "y": y_def
                },
                "params": [{
                    "name": "hover",
                    "select": {"type": "point", "on": "mouseover", "nearest": True, "clear": "mouseout"}
                }]
            }
        ]
        
    elif chart_type == "bar":
        spec["mark"] = {
            "type": "bar",
            "cornerRadiusEnd": 6,
            "color": "#2563eb",
            "width": {"band": 0.6}
        }
        
        # Handle Aggregation
        if not y:
            # Count mode - no filter needed, Vega-Lite handles nulls in aggregation
            spec["encoding"] = {
                "x": {"field": x, "type": x_type, "axis": {"labelAngle": -45, "labelLimit": 100}, "sort": "-y"},
                "y": {"aggregate": "count", "title": "Count"},
                "tooltip": [
                    {"field": x, "type": x_type},
                    {"aggregate": "count", "title": "Count", "format": ","}
                ]
            }
        elif y_aggregate:
            # Custom aggregation mode (sum, mean, min, max)
            agg_title = f"{y_aggregate.upper()} of {y}"
            spec["encoding"] = {
                "x": {"field": x, "type": x_type, "axis": {"labelAngle": 0}, "sort": "-y"},
                "y": {"field": y, "aggregate": y_aggregate, "title": agg_title, "type": "quantitative"},
                "tooltip": [
                    {"field": x, "type": x_type},
                    {"field": y, "aggregate": y_aggregate, "title": agg_title, "format": ","}
                ]
            }
        else:
            # Standard mode (no aggregation)
            spec["encoding"] = {
                "x": {"field": x, "type": x_type, "axis": {"labelAngle": 0}},
                "y": {"field": y, "type": y_type},
                "tooltip": [
                    {"field": x, "type": x_type},
                    {"field": y, "type": y_type, "format": ","}
                ]
            }
            
    elif chart_type == "donut":
        spec["mark"] = {"type": "arc", "innerRadius": 50, "outerRadius": 100}
        # No filter - Vega-Lite handles nulls in categorical count aggregation
        spec["encoding"] = {
            "theta": {"aggregate": "count", "stack": True},
            "color": {
                "field": x, 
                "type": "nominal", 
                "legend": {"title": None, "orient": "right"},
                "scale": {"scheme": "category10"}
            },
            "order": {"aggregate": "count", "sort": "descending"},
            "tooltip": [
                {"field": x, "type": "nominal"},
                {"aggregate": "count", "title": "Count", "format": ","}
            ]
        }
        
    elif chart_type == "scatter":
        spec["mark"] = {
            "type": "circle",
            "size": 80,
            "opacity": 0.6,
            "color": "#2563eb"
        }
        
        tooltip = [{"field": x, "type": x_type}]
        if y:
            tooltip.append({"field": y, "type": y_type, "format": ","})

        spec["encoding"] = {
            "x": {"field": x, "type": x_type},
            "tooltip": tooltip
        }
        
        if y:
            spec["encoding"]["y"] = {"field": y, "type": y_type}

    elif chart_type == "histogram":
        # Correct implementation of histogram using bar mark + binning
        spec["mark"] = {
            "type": "bar",
            "color": "#2563eb",
            "cornerRadiusEnd": 4
        }
        spec["encoding"] = {
            "x": {
                "field": x, 
                "bin": {"maxbins": 20},
                "title": x
            },
            "y": {
                "aggregate": "count",
                "title": "Frequency"
            },
            "tooltip": [
                {"field": x, "bin": True, "title": x},
                {"aggregate": "count", "title": "Count"}
            ]
        }
        
    elif chart_type == "stacked_bar":
        # Stacked bar chart: X = Category1, Color = Category2, Y = Count/Value
        spec["mark"] = {
            "type": "bar",
            "cornerRadiusEnd": 4
        }
        spec["encoding"] = {
            "x": {"field": x, "type": x_type, "axis": {"labelAngle": 0}},
            "color": {
                "field": color if color else x,
                "type": "nominal",
                "scale": {"scheme": "tableau10"},
                "legend": {"title": None, "orient": "top"}
            },
            "tooltip": [
                {"field": x, "type": x_type},
                {"field": color if color else x, "type": "nominal"}
            ]
        }
        if y:
            spec["encoding"]["y"] = {"field": y, "type": y_type}
            spec["encoding"]["tooltip"].append({"field": y, "type": y_type, "format": ","})
        else:
            spec["encoding"]["y"] = {"aggregate": "count", "title": "Count"}
            spec["encoding"]["tooltip"].append({"aggregate": "count", "title": "Count"})
            
    elif chart_type == "heatmap":
        # Heatmap: X = Category1, Y = Category2, Color = Count/Value
        spec["mark"] = {"type": "rect"}
        spec["encoding"] = {
            "x": {"field": x, "type": x_type, "axis": {"labelAngle": 0}},
            "y": {"field": y, "type": y_type} if y else {"field": x, "type": x_type},
            "color": {
                "aggregate": "count",
                "scale": {"scheme": "blues"},
                "legend": {"title": "Count"}
            },
            "tooltip": [
                {"field": x, "type": x_type},
                {"field": y, "type": y_type} if y else {"field": x, "type": x_type},
                {"aggregate": "count", "title": "Count"}
            ]
        }
        
    elif chart_type == "tick":
        # Tick chart for 1D distribution (good for anomalies)
        spec["mark"] = {
            "type": "tick",
            "color": "#ef4444", # Red for anomalies
            "thickness": 2,
            "size": 25
        }
        spec["encoding"] = {
            "x": {"field": x, "type": x_type, "axis": {"title": x}},
            "tooltip": [
                {"field": x, "type": x_type}
            ]
        }
        
    # Common Encodings for non-layered charts
    if "layer" not in spec:
        if color and chart_type not in ["stacked_bar", "heatmap", "donut"]:
            spec["encoding"]["color"] = {
                "field": color,
                "legend": {"title": None, "orient": "top"},
                "scale": {"scheme": "tableau10"}
            }
    
    # Add zoom/pan for scatter and area charts
    if chart_type in ["scatter"]:
        spec["params"] = [{
            "name": "zoom",
            "select": "interval",
            "bind": "scales"
        }]
        
    return spec


def generate_correlation_matrix_spec(
    numeric_columns: list,
    title: str = "Correlation Matrix"
) -> Dict[str, Any]:
    """
    Generate a Vega-Lite specification for a correlation matrix (scatter plot matrix).
    
    Args:
        numeric_columns: List of numeric column names to include
        title: Chart title
        
    Returns:
        Dictionary containing the Vega-Lite specification with repeat
    """
    # Limit to max 5 columns for readability
    cols = numeric_columns[:5]
    
    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
        "title": {
            "text": title,
            "fontSize": 18,
            "anchor": "start",
            "font": "Inter, sans-serif",
            "fontWeight": 600,
            "color": "#111827"
        },
        "data": {"name": "table"},
        "repeat": {
            "row": cols,
            "column": cols
        },
        "spec": {
            "width": 120,
            "height": 120,
            "mark": {
                "type": "circle",
                "size": 10,
                "opacity": 0.5,
                "color": "#2563eb"
            },
            "encoding": {
                "x": {
                    "field": {"repeat": "column"},
                    "type": "quantitative",
                    "scale": {"zero": False},
                    "axis": {"titleFontSize": 10, "labelFontSize": 8}
                },
                "y": {
                    "field": {"repeat": "row"},
                    "type": "quantitative",
                    "scale": {"zero": False},
                    "axis": {"titleFontSize": 10, "labelFontSize": 8}
                },
                "tooltip": [
                    {"field": {"repeat": "column"}, "type": "quantitative"},
                    {"field": {"repeat": "row"}, "type": "quantitative"}
                ]
            },
            "params": [{
                "name": "zoom",
                "select": "interval",
                "bind": "scales"
            }]
        },
        "config": {
            "font": "Inter, sans-serif",
            "axis": {
                "grid": True,
                "gridColor": "#f3f4f6",
                "domain": False
            },
            "view": {"stroke": "transparent"}
        }
    }
    
    return spec
