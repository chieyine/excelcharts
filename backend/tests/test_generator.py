"""
Unit tests for the generator service.
"""
import pytest
from app.services.generator import generate_vega_spec


@pytest.mark.unit
def test_generate_vega_spec_line():
    """Test generating a line chart spec."""
    spec = generate_vega_spec(
        chart_type="line",
        x="date",
        y="value",
        title="Test Line Chart",
        x_type="temporal",
        y_type="quantitative"
    )
    
    assert spec["$schema"] == "https://vega.github.io/schema/vega-lite/v5.json"
    assert spec["title"]["text"] == "Test Line Chart"
    assert spec["mark"]["type"] == "line"
    assert spec["encoding"]["x"]["field"] == "date"
    assert spec["encoding"]["x"]["type"] == "temporal"
    assert spec["encoding"]["y"]["field"] == "value"
    assert spec["encoding"]["y"]["type"] == "quantitative"


@pytest.mark.unit
def test_generate_vega_spec_bar():
    """Test generating a bar chart spec."""
    spec = generate_vega_spec(
        chart_type="bar",
        x="category",
        y="count",
        title="Test Bar Chart",
        x_type="nominal",
        y_type="quantitative"
    )
    
    assert spec["mark"]["type"] == "bar"
    assert spec["encoding"]["x"]["field"] == "category"
    assert spec["encoding"]["x"]["type"] == "nominal"
    assert spec["encoding"]["y"]["field"] == "count"


@pytest.mark.unit
def test_generate_vega_spec_scatter():
    """Test generating a scatter chart spec."""
    spec = generate_vega_spec(
        chart_type="scatter",
        x="x",
        y="y",
        title="Test Scatter Chart",
        x_type="quantitative",
        y_type="quantitative"
    )
    
    assert spec["mark"]["type"] == "circle"
    assert spec["encoding"]["x"]["field"] == "x"
    assert spec["encoding"]["y"]["field"] == "y"


@pytest.mark.unit
def test_generate_vega_spec_histogram():
    """Test generating a histogram spec."""
    spec = generate_vega_spec(
        chart_type="histogram",
        x="value",
        title="Test Histogram",
        x_type="quantitative"
    )
    
    assert spec["mark"]["type"] == "histogram"
    assert spec["encoding"]["x"]["field"] == "value"
    assert "y" not in spec["encoding"]


@pytest.mark.unit
def test_generate_vega_spec_with_color():
    """Test generating a spec with color encoding."""
    spec = generate_vega_spec(
        chart_type="bar",
        x="category",
        y="value",
        title="Test Chart",
        color="group",
        x_type="nominal",
        y_type="quantitative"
    )
    
    assert "color" in spec["encoding"]
    assert spec["encoding"]["color"]["field"] == "group"


@pytest.mark.unit
def test_generate_vega_spec_defaults():
    """Test that default values are set correctly."""
    spec = generate_vega_spec(
        chart_type="bar",
        x="x",
        title="Test"
    )
    
    assert spec["width"] == "container"
    assert spec["height"] == 400
    assert spec["config"]["font"] == "Inter, sans-serif"
    assert spec["data"]["name"] == "table"


@pytest.mark.unit
def test_generate_vega_spec_line_interpolation():
    """Test that line charts have smooth interpolation."""
    spec = generate_vega_spec(
        chart_type="line",
        x="x",
        y="y",
        title="Test"
    )
    
    assert spec["mark"]["interpolate"] == "monotone"
    assert spec["mark"]["strokeWidth"] == 3


@pytest.mark.unit
def test_generate_vega_spec_bar_rounded():
    """Test that bar charts have rounded corners."""
    spec = generate_vega_spec(
        chart_type="bar",
        x="x",
        y="y",
        title="Test"
    )
    
    assert spec["mark"]["cornerRadiusEnd"] == 4

