"""
Chart inference service.

This module analyzes dataset profiles and infers the best chart types
based on data characteristics using deterministic rules.
"""
import logging
from typing import List, Optional, Dict, Any
from app.core.schemas import ColumnProfile, ChartCandidate, DatasetProfile
from app.services.generator import generate_vega_spec, generate_correlation_matrix_spec

logger = logging.getLogger(__name__)

def infer_charts(profile: DatasetProfile, sample_data: List[Dict[str, Any]] = None) -> List[ChartCandidate]:
    """
    Infer chart candidates from a dataset profile.
    
    Uses deterministic rules + AI to identify the best chart types:
    - AI analyzes content to recommend specific visualizations
    - Heuristics map data types to standard charts (Line, Bar, Scatter)
    
    Args:
        profile: Dataset profile containing column metadata
        sample_data: Optional sample rows for AI analysis
        
    Returns:
        List of chart candidates sorted by score (highest first)
        Returns top 5 candidates
    """
    candidates = []
    
    # 1. Identify Roles
    temporal_cols = [c for c in profile.columns if c.dtype == 'temporal']
    numeric_cols = [c for c in profile.columns if c.dtype == 'numeric']
    nominal_cols = [c for c in profile.columns if c.dtype == 'nominal']
    ordinal_cols = [c for c in profile.columns if c.dtype == 'ordinal']
    
    # Combined categorical
    categorical_cols = nominal_cols + ordinal_cols
    
    # 2. Rule: TIME + VALUE = LINE CHART
    # This is the gold standard for time series
    for time_col in temporal_cols:
        for num_col in numeric_cols:
            # Check if num_col is an ID? (skip IDs)
            if "id" in num_col.name.lower() and num_col.unique_count == profile.row_count:
                continue
                
            spec = generate_vega_spec(
                chart_type="area",
                x=time_col.name,
                y=num_col.name,
                title=f"{num_col.name} over Time",
                x_type="temporal",
                y_type="quantitative"
            )
            
            candidates.append(ChartCandidate(
                chart_type="area",
                x_column=time_col.name,
                y_column=num_col.name,
                title=f"{num_col.name} over Time",
                description=f"Trend of {num_col.name} over {time_col.name}",
                score=0.95, # High confidence
                spec=spec
            ))
            
    # 3. Rule: CATEGORY + VALUE = BAR CHART
    for cat_col in categorical_cols:
        if cat_col.unique_count > 20:
            continue # Too many bars
            
        for num_col in numeric_cols:
            if "id" in num_col.name.lower(): 
                continue
            
            # Default bar chart (no aggregation - assumes row-level data)
            spec = generate_vega_spec(
                chart_type="bar",
                x=cat_col.name,
                y=num_col.name,
                title=f"{num_col.name} by {cat_col.name}",
                x_type="nominal",
                y_type="quantitative"
            )
            
            candidates.append(ChartCandidate(
                chart_type="bar",
                x_column=cat_col.name,
                y_column=num_col.name,
                title=f"{num_col.name} by {cat_col.name}",
                description=f"Comparison of {num_col.name} across {cat_col.name}",
                score=0.85, 
                spec=spec
            ))
            
            # SUM aggregation variant
            spec_sum = generate_vega_spec(
                chart_type="bar",
                x=cat_col.name,
                y=num_col.name,
                title=f"Total {num_col.name} by {cat_col.name}",
                x_type="nominal",
                y_type="quantitative",
                y_aggregate="sum"
            )
            
            candidates.append(ChartCandidate(
                chart_type="bar",
                x_column=cat_col.name,
                y_column=num_col.name,
                title=f"Total {num_col.name} by {cat_col.name}",
                description=f"Sum of {num_col.name} for each {cat_col.name}",
                score=0.82, 
                spec=spec_sum
            ))
            
            # AVERAGE aggregation variant
            spec_avg = generate_vega_spec(
                chart_type="bar",
                x=cat_col.name,
                y=num_col.name,
                title=f"Average {num_col.name} by {cat_col.name}",
                x_type="nominal",
                y_type="quantitative",
                y_aggregate="mean"
            )
            
            candidates.append(ChartCandidate(
                chart_type="bar",
                x_column=cat_col.name,
                y_column=num_col.name,
                title=f"Average {num_col.name} by {cat_col.name}",
                description=f"Average of {num_col.name} for each {cat_col.name}",
                score=0.80, 
                spec=spec_avg
            ))


    # 4. Rule: NUMERIC + NUMERIC = SCATTER
    if len(numeric_cols) >= 2:
        # Try all pairs
        for i in range(len(numeric_cols)):
            col_x = numeric_cols[i]
            if "id" in col_x.name.lower(): continue
            
            for j in range(i+1, len(numeric_cols)):
                col_y = numeric_cols[j]
                if "id" in col_y.name.lower(): continue

                spec = generate_vega_spec(
                    chart_type="scatter",
                    x=col_x.name,
                    y=col_y.name,
                    title=f"{col_x.name} vs {col_y.name}",
                    x_type="quantitative",
                    y_type="quantitative"
                )
                
                candidates.append(ChartCandidate(
                    chart_type="scatter",
                    x_column=col_x.name,
                    y_column=col_y.name,
                    title=f"{col_x.name} vs {col_y.name}",
                    description=f"Correlation between {col_x.name} and {col_y.name}",
                    score=0.70, 
                    spec=spec
                ))
    
    # 5. Rule: SINGLE NUMERIC = HISTOGRAM
    for num_col in numeric_cols:
        if "id" in num_col.name.lower(): continue
        
        spec = generate_vega_spec(
            chart_type="histogram",
            x=num_col.name,
            title=f"Distribution of {num_col.name}",
            x_type="quantitative"
        )
        
        candidates.append(ChartCandidate(
            chart_type="histogram",
            x_column=num_col.name,
            title=f"Distribution of {num_col.name}",
            description=f"Frequency distribution of {num_col.name}",
            score=0.60,
            spec=spec
        ))

    # 6. Rule: SINGLE CATEGORICAL = BAR COUNT / DONUT
    # Generate a chart for EVERY categorical column
    for cat_col in categorical_cols:
        # Donut for simple Yes/No or small categories (≤5 unique)
        if cat_col.unique_count <= 5:
            spec = generate_vega_spec(
                chart_type="donut",
                x=cat_col.name,
                title=f"Distribution of {cat_col.name}",
                x_type="nominal"
            )
            candidates.append(ChartCandidate(
                chart_type="donut",
                x_column=cat_col.name,
                title=f"Distribution of {cat_col.name}",
                description=f"Proportion of {cat_col.name}",
                score=0.80, # High relevance for surveys
                spec=spec
            ))
        # Bar Chart for all categorical columns (regardless of unique count)
        # Limit to top 30 categories for readability
        spec = generate_vega_spec(
            chart_type="bar",
            x=cat_col.name,
            title=f"Count by {cat_col.name}",
            x_type="nominal"
        )
        candidates.append(ChartCandidate(
            chart_type="bar",
            x_column=cat_col.name,
            title=f"Count by {cat_col.name}",
            description=f"Frequency of {cat_col.name}",
            score=0.70 if cat_col.unique_count > 20 else 0.75,  # Lower score for high-cardinality
            spec=spec
        ))

    # 7. Rule: SINGLE TEMPORAL = AREA COUNT (Responses over time)
    # Excellent for "When did people fill out the form?"
    for time_col in temporal_cols:
        spec = generate_vega_spec(
            chart_type="area",
            x=time_col.name,
            title=f"Responses over {time_col.name}",
            x_type="temporal"
        )
        candidates.append(ChartCandidate(
            chart_type="area",
            x_column=time_col.name,
            title=f"Responses over {time_col.name}",
            description=f"Volume of records over time",
            score=0.70,
            spec=spec
        ))

    # 8. Rule: CATEGORICAL + CATEGORICAL = HEATMAP
    # Excellent for cross-tabulation (e.g., "Department × Gender")
    if len(categorical_cols) >= 2:
        for i in range(min(3, len(categorical_cols))):  # Limit combinations
            cat1 = categorical_cols[i]
            if cat1.unique_count > 15:
                continue
            for j in range(i+1, min(4, len(categorical_cols))):
                cat2 = categorical_cols[j]
                if cat2.unique_count > 15:
                    continue
                    
                spec = generate_vega_spec(
                    chart_type="heatmap",
                    x=cat1.name,
                    y=cat2.name,
                    title=f"{cat1.name} vs {cat2.name}",
                    x_type="nominal",
                    y_type="nominal"
                )
                candidates.append(ChartCandidate(
                    chart_type="heatmap",
                    x_column=cat1.name,
                    y_column=cat2.name,
                    title=f"{cat1.name} vs {cat2.name}",
                    description=f"Cross-tabulation of {cat1.name} and {cat2.name}",
                    score=0.65,
                    spec=spec
                ))
                
    # 9. Rule: CATEGORICAL + CATEGORICAL + NUMERIC = STACKED BAR
    # Excellent for grouped comparisons
    if len(categorical_cols) >= 2 and len(numeric_cols) >= 1:
        cat1 = categorical_cols[0]
        cat2 = categorical_cols[1] if len(categorical_cols) > 1 else categorical_cols[0]
        num_col = numeric_cols[0]
        
        if cat1.unique_count <= 10 and cat2.unique_count <= 10:
            spec = generate_vega_spec(
                chart_type="stacked_bar",
                x=cat1.name,
                y=num_col.name,
                title=f"{num_col.name} by {cat1.name} (grouped by {cat2.name})",
                x_type="nominal",
                y_type="quantitative",
                color=cat2.name
            )
            candidates.append(ChartCandidate(
                chart_type="stacked_bar",
                x_column=cat1.name,
                y_column=num_col.name,
                color_column=cat2.name,
                title=f"{num_col.name} by {cat1.name}",
                description=f"Grouped comparison of {num_col.name}",
                score=0.72,
                spec=spec
            ))

    # 10. Rule: MULTIPLE NUMERIC = CORRELATION MATRIX
    # When there are 3+ numeric columns, offer a scatter plot matrix
    if len(numeric_cols) >= 3:
        numeric_col_names = [c.name for c in numeric_cols if "id" not in c.name.lower()]
        if len(numeric_col_names) >= 3:
            spec = generate_correlation_matrix_spec(
                numeric_columns=numeric_col_names[:5],  # Limit to 5 for readability
                title="Correlation Matrix"
            )
            candidates.append(ChartCandidate(
                chart_type="correlation_matrix",
                x_column=numeric_col_names[0],
                y_column=numeric_col_names[1],
                title="Correlation Matrix",
                description=f"Scatter plot matrix of {len(numeric_col_names[:5])} numeric variables",
                score=0.68,
                spec=spec
            ))
    
    # Sort by score DESC
    candidates.sort(key=lambda x: x.score, reverse=True)
    
    # Return up to 50 charts to cover all columns in large datasets
    result = candidates[:50]
    logger.info(f"Generated {len(result)} chart candidates from {len(candidates)} total candidates")
    
    return result
