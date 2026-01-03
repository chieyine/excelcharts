"""
Unit tests for the inference service.
"""
import pytest
from app.services.inference import infer_charts
from app.core.schemas import DatasetProfile, ColumnProfile, ChartCandidate


@pytest.fixture
def time_series_profile():
    """Create a profile with temporal and numeric columns."""
    return DatasetProfile(
        row_count=10,
        col_count=2,
        columns=[
            ColumnProfile(
                name="date",
                original_name="date",
                dtype="temporal",
                null_count=0,
                unique_count=10,
                examples=["2024-01-01", "2024-01-02"],
                min="2024-01-01T00:00:00",
                max="2024-01-10T00:00:00"
            ),
            ColumnProfile(
                name="value",
                original_name="value",
                dtype="numeric",
                null_count=0,
                unique_count=10,
                examples=[10, 20],
                min=10.0,
                max=100.0,
                mean=55.0
            )
        ]
    )


@pytest.fixture
def categorical_profile():
    """Create a profile with categorical and numeric columns."""
    return DatasetProfile(
        row_count=5,
        col_count=2,
        columns=[
            ColumnProfile(
                name="category",
                original_name="category",
                dtype="nominal",
                null_count=0,
                unique_count=3,
                examples=["A", "B", "C"]
            ),
            ColumnProfile(
                name="count",
                original_name="count",
                dtype="numeric",
                null_count=0,
                unique_count=5,
                examples=[10, 20, 30],
                min=10.0,
                max=50.0,
                mean=30.0
            )
        ]
    )


@pytest.fixture
def numeric_pair_profile():
    """Create a profile with two numeric columns."""
    return DatasetProfile(
        row_count=10,
        col_count=2,
        columns=[
            ColumnProfile(
                name="x",
                original_name="x",
                dtype="numeric",
                null_count=0,
                unique_count=10,
                examples=[1, 2, 3],
                min=1.0,
                max=10.0,
                mean=5.5
            ),
            ColumnProfile(
                name="y",
                original_name="y",
                dtype="numeric",
                null_count=0,
                unique_count=10,
                examples=[10, 20, 30],
                min=10.0,
                max=100.0,
                mean=55.0
            )
        ]
    )


@pytest.mark.unit
def test_infer_charts_time_series(time_series_profile):
    """Test inferring charts for time series data."""
    candidates = infer_charts(time_series_profile)
    
    assert len(candidates) > 0
    assert candidates[0].chart_type == "line"
    assert candidates[0].x_column == "date"
    assert candidates[0].y_column == "value"
    assert candidates[0].score >= 0.9  # High confidence for time series


@pytest.mark.unit
def test_infer_charts_categorical(categorical_profile):
    """Test inferring charts for categorical data."""
    candidates = infer_charts(categorical_profile)
    
    assert len(candidates) > 0
    # Should have bar chart as top candidate
    bar_charts = [c for c in candidates if c.chart_type == "bar"]
    assert len(bar_charts) > 0


@pytest.mark.unit
def test_infer_charts_numeric_pair(numeric_pair_profile):
    """Test inferring charts for numeric pair data."""
    candidates = infer_charts(numeric_pair_profile)
    
    assert len(candidates) > 0
    # Should have scatter chart
    scatter_charts = [c for c in candidates if c.chart_type == "scatter"]
    assert len(scatter_charts) > 0


@pytest.mark.unit
def test_infer_charts_returns_top_5():
    """Test that infer_charts returns at most 5 candidates."""
    profile = DatasetProfile(
        row_count=10,
        col_count=5,
        columns=[
            ColumnProfile(
                name=f"col{i}",
                original_name=f"col{i}",
                dtype="numeric",
                null_count=0,
                unique_count=10,
                examples=[1, 2, 3],
                min=1.0,
                max=10.0,
                mean=5.5
            )
            for i in range(5)
        ]
    )
    
    candidates = infer_charts(profile)
    assert len(candidates) <= 5


@pytest.mark.unit
def test_infer_charts_sorted_by_score():
    """Test that candidates are sorted by score descending."""
    profile = DatasetProfile(
        row_count=10,
        col_count=3,
        columns=[
            ColumnProfile(
                name="date",
                original_name="date",
                dtype="temporal",
                null_count=0,
                unique_count=10,
                examples=["2024-01-01"],
                min="2024-01-01T00:00:00",
                max="2024-01-10T00:00:00"
            ),
            ColumnProfile(
                name="value",
                original_name="value",
                dtype="numeric",
                null_count=0,
                unique_count=10,
                examples=[10],
                min=10.0,
                max=100.0,
                mean=55.0
            ),
            ColumnProfile(
                name="category",
                original_name="category",
                dtype="nominal",
                null_count=0,
                unique_count=3,
                examples=["A"]
            )
        ]
    )
    
    candidates = infer_charts(profile)
    
    # Check scores are descending
    for i in range(len(candidates) - 1):
        assert candidates[i].score >= candidates[i + 1].score


@pytest.mark.unit
def test_infer_charts_skips_id_columns():
    """Test that ID columns are skipped in chart inference."""
    profile = DatasetProfile(
        row_count=10,
        col_count=2,
        columns=[
            ColumnProfile(
                name="id",
                original_name="id",
                dtype="numeric",
                null_count=0,
                unique_count=10,  # All unique (ID column)
                examples=[1, 2, 3],
                min=1.0,
                max=10.0,
                mean=5.5
            ),
            ColumnProfile(
                name="value",
                original_name="value",
                dtype="numeric",
                null_count=0,
                unique_count=10,
                examples=[10, 20],
                min=10.0,
                max=100.0,
                mean=55.0
            )
        ]
    )
    
    candidates = infer_charts(profile)
    
    # Should not have charts using id column
    for candidate in candidates:
        assert "id" not in candidate.x_column.lower() or candidate.chart_type == "histogram"

