"""
Enhanced natural language insights generation.

Generates statistical insights and patterns from data.
"""
import logging
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from app.core.schemas import DatasetProfile, ColumnProfile

logger = logging.getLogger(__name__)


def calculate_trend(series: pd.Series) -> Optional[Dict[str, Any]]:
    """
    Calculate trend direction and strength.
    
    Returns:
        Dict with direction ('increasing', 'decreasing', 'stable') and percentage change
    """
    if len(series) < 2:
        return None
    
    numeric_series = pd.to_numeric(series, errors='coerce').dropna()
    if len(numeric_series) < 2:
        return None
    
    first_val = numeric_series.iloc[0]
    last_val = numeric_series.iloc[-1]
    
    if pd.isna(first_val) or pd.isna(last_val) or first_val == 0:
        return None
    
    pct_change = ((last_val - first_val) / abs(first_val)) * 100
    
    # Determine direction
    if abs(pct_change) < 5:
        direction = 'stable'
    elif pct_change > 0:
        direction = 'increasing'
    else:
        direction = 'decreasing'
    
    return {
        'direction': direction,
        'percentage_change': round(pct_change, 1),
        'first_value': float(first_val),
        'last_value': float(last_val)
    }


def detect_outliers(series: pd.Series) -> Optional[Dict[str, Any]]:
    """
    Detect outliers using IQR method.
    
    Returns:
        Dict with outlier count and examples
    """
    numeric_series = pd.to_numeric(series, errors='coerce').dropna()
    if len(numeric_series) < 4:
        return None
    
    Q1 = numeric_series.quantile(0.25)
    Q3 = numeric_series.quantile(0.75)
    IQR = Q3 - Q1
    
    if IQR == 0:
        return None
    
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    
    outliers = numeric_series[(numeric_series < lower_bound) | (numeric_series > upper_bound)]
    
    if len(outliers) > 0:
        return {
            'count': len(outliers),
            'percentage': round((len(outliers) / len(numeric_series)) * 100, 1),
            'examples': outliers.head(3).tolist()
        }
    
    return None


def generate_insights(profile: DatasetProfile, df: pd.DataFrame) -> List[str]:
    """
    Generate enhanced natural language insights from data.
    
    Returns:
        List of insight strings
    """
    insights = []
    
    # Find temporal and numeric columns for trend analysis
    temporal_cols = [c for c in profile.columns if c.dtype == 'temporal']
    numeric_cols = [c for c in profile.columns if c.dtype == 'numeric']
    
    # Insight 1: Trend analysis for time series
    if temporal_cols and numeric_cols:
        time_col = temporal_cols[0]
        num_col = numeric_cols[0]
        
        if time_col.name in df.columns and num_col.name in df.columns:
            # Sort by time
            df_sorted = df.sort_values(by=time_col.name)
            series = df_sorted[num_col.name]
            
            trend = calculate_trend(series)
            if trend:
                direction_emoji = {
                    'increasing': '📈',
                    'decreasing': '📉',
                    'stable': '➡️'
                }
                emoji = direction_emoji.get(trend['direction'], '📊')
                
                if trend['direction'] == 'increasing':
                    insight = f"{emoji} {num_col.name} grew {abs(trend['percentage_change']):.1f}% from {trend['first_value']:.1f} to {trend['last_value']:.1f}"
                elif trend['direction'] == 'decreasing':
                    insight = f"{emoji} {num_col.name} decreased {abs(trend['percentage_change']):.1f}% from {trend['first_value']:.1f} to {trend['last_value']:.1f}"
                else:
                    insight = f"{emoji} {num_col.name} remained relatively stable around {trend['first_value']:.1f}"
                
                insights.append(insight)
    
    # Insight 2: Outlier detection
    for num_col in numeric_cols[:2]:  # Check first 2 numeric columns
        if num_col.name in df.columns:
            series = pd.to_numeric(df[num_col.name], errors='coerce').dropna()
            if len(series) > 4:
                outliers = detect_outliers(series)
                if outliers and outliers['count'] > 0:
                    insights.append(
                        f"⚠️ Found {outliers['count']} unusual values in {num_col.name} "
                        f"({outliers['percentage']}% of data) — worth investigating"
                    )
    
    # Insight 3: Comparison insights for categorical data
    categorical_cols = [c for c in profile.columns if c.dtype in ['nominal', 'ordinal']]
    if categorical_cols and numeric_cols:
        cat_col = categorical_cols[0]
        num_col = numeric_cols[0]
        
        if cat_col.name in df.columns and num_col.name in df.columns:
            grouped = df.groupby(cat_col.name)[num_col.name].mean().sort_values(ascending=False)
            if len(grouped) > 1:
                top = grouped.iloc[0]
                second = grouped.iloc[1]
                top_cat = grouped.index[0]
                
                if top > 0:
                    ratio = top / second if second > 0 else float('inf')
                    if ratio > 1.5:
                        insights.append(
                            f"🏆 {top_cat} leads with {num_col.name} of {top:.1f}, "
                            f"{ratio:.1f}x higher than {grouped.index[1]}"
                        )
    
    # Insight 4: Data quality insights
    total_cells = profile.row_count * profile.col_count
    total_nulls = sum(c.null_count for c in profile.columns)
    if total_nulls > 0:
        null_percentage = (total_nulls / total_cells) * 100
        if null_percentage > 5:
            insights.append(
                f"ℹ️ Dataset contains {total_nulls} missing values ({null_percentage:.1f}%) "
                f"— consider data cleaning"
            )
    
    # Insight 5: Distribution insights
    for num_col in numeric_cols[:1]:
        if num_col.name in df.columns:
            series = pd.to_numeric(df[num_col.name], errors='coerce').dropna()
            if len(series) > 10:
                cv = series.std() / series.mean() if series.mean() != 0 else 0
                if cv > 1.0:
                    insights.append(
                        f"📊 {num_col.name} shows high variability (coefficient of variation: {cv:.2f})"
                    )
    
    # Ensure we have at least one insight
    if not insights:
        insights.append(f"📊 Analyzed {profile.row_count} rows and {profile.col_count} columns")
    
    return insights[:3]  # Return top 3 insights

