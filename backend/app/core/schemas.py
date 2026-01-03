from pydantic import BaseModel
from typing import List, Optional, Any, Dict, Union

class ColumnProfile(BaseModel):
    name: str
    original_name: str
    dtype: str  # 'numeric', 'temporal', 'nominal', 'ordinal'
    null_count: int
    unique_count: int
    examples: List[Any]
    min: Optional[Union[float, str]] = None  # float for numeric, ISO string for temporal
    max: Optional[Union[float, str]] = None  # float for numeric, ISO string for temporal
    mean: Optional[float] = None

class DatasetProfile(BaseModel):
    row_count: int
    col_count: int
    columns: List[ColumnProfile]

class ChartCandidate(BaseModel):
    chart_type: str  # 'line', 'bar', 'scatter', 'histogram', 'table'
    x_column: str
    y_column: Optional[str] = None
    color_column: Optional[str] = None
    title: str
    description: str
    score: float
    spec: Dict[str, Any]  # The Vega-Lite spec

class AnalysisResult(BaseModel):
    filename: str
    profile: DatasetProfile
    recommended_chart: ChartCandidate  # Now always required (fallback provided if no candidates)
    alternatives: List[ChartCandidate]
    dataset: List[Dict[str, Any]]
    insights: List[str] = []  # Enhanced natural language insights
    surprise: Optional[Dict[str, Any]] = None  # Surprise me discovery
