"""
"Surprise Me" feature - discover unexpected patterns and insights.
"""
import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from app.core.schemas import DatasetProfile, ChartCandidate
from app.services.generator import generate_vega_spec
from app.services.ai_insights import explain_anomaly

logger = logging.getLogger(__name__)


def find_surprising_correlation(profile: DatasetProfile, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """
    Find unexpected correlations between numeric columns.
    
    Returns:
        Dict with correlation info and chart candidate
    """
    numeric_cols = [c for c in profile.columns if c.dtype == 'numeric']
    
    if len(numeric_cols) < 2:
        return None
    
    # Calculate correlations
    correlations = {}
    for i, col1 in enumerate(numeric_cols):
        if col1.name not in df.columns:
            continue
        for col2 in numeric_cols[i+1:]:
            if col2.name not in df.columns:
                continue
            
            series1 = pd.to_numeric(df[col1.name], errors='coerce')
            series2 = pd.to_numeric(df[col2.name], errors='coerce')
            
            # Remove NaN pairs
            valid_mask = series1.notna() & series2.notna()
            if valid_mask.sum() < 3:
                continue
            
            corr = series1[valid_mask].corr(series2[valid_mask])
            
            if not pd.isna(corr):
                # Look for strong correlations (positive or negative)
                if abs(corr) > 0.7:
                    correlations[(col1.name, col2.name)] = corr
    
    if not correlations:
        return None
    
    # Find strongest correlation
    best_pair = max(correlations.items(), key=lambda x: abs(x[1]))
    (col1, col2), corr_value = best_pair
    
    # Generate insight
    if corr_value > 0.8:
        insight = f"🎯 Strong positive correlation ({corr_value:.2f}) between {col1} and {col2} — they move together!"
    elif corr_value < -0.8:
        insight = f"🎯 Strong negative correlation ({abs(corr_value):.2f}) between {col1} and {col2} — when one goes up, the other goes down!"
    else:
        insight = f"🔗 Interesting correlation ({corr_value:.2f}) between {col1} and {col2}"
    
    # Create scatter plot
    spec = generate_vega_spec(
        chart_type="scatter",
        x=col1,
        y=col2,
        title=f"{col1} vs {col2} (Correlation: {corr_value:.2f})",
        x_type="quantitative",
        y_type="quantitative"
    )
    
    return {
        'insight': insight,
        'chart_type': 'scatter',
        'x_column': col1,
        'y_column': col2,
        'correlation': corr_value,
        'spec': spec
    }


def find_growth_anomaly(profile: DatasetProfile, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """
    Find unexpected growth patterns.
    """
    temporal_cols = [c for c in profile.columns if c.dtype == 'temporal']
    numeric_cols = [c for c in profile.columns if c.dtype == 'numeric']
    
    if not temporal_cols or not numeric_cols:
        return None
    
    time_col = temporal_cols[0]
    num_col = numeric_cols[0]
    
    if time_col.name not in df.columns or num_col.name not in df.columns:
        return None
    
    # Sort by time
    df_sorted = df.sort_values(by=time_col.name).copy()
    series = pd.to_numeric(df_sorted[num_col.name], errors='coerce')
    
    if len(series) < 3:
        return None
    
    # Calculate period-over-period growth
    pct_changes = series.pct_change().dropna()
    
    if len(pct_changes) < 2:
        return None
    
    # Find largest jump
    max_jump_idx = pct_changes.idxmax()
    max_jump_value = pct_changes.max()
    
    if max_jump_value > 0.5:  # 50% jump
        jump_date = df_sorted.loc[max_jump_idx, time_col.name]
        insight = f"🚀 Surprising spike: {num_col.name} jumped {max_jump_value*100:.0f}% on {jump_date} — what happened?"
        
        spec = generate_vega_spec(
            chart_type="line",
            x=time_col.name,
            y=num_col.name,
            title=f"{num_col.name} Growth Pattern",
            x_type="temporal",
            y_type="quantitative"
        )
        
        return {
            'insight': insight,
            'chart_type': 'line',
            'x_column': time_col.name,
            'y_column': num_col.name,
            'spec': spec
        }
    
    return None


def find_hidden_leader(profile: DatasetProfile, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """
    Find category with unexpected performance (high growth but low absolute value).
    """
    categorical_cols = [c for c in profile.columns if c.dtype in ['nominal', 'ordinal']]
    numeric_cols = [c for c in profile.columns if c.dtype == 'numeric']
    
    if not categorical_cols or not numeric_cols:
        return None
    
    cat_col = categorical_cols[0]
    num_col = numeric_cols[0]
    
    if cat_col.name not in df.columns or num_col.name not in df.columns:
        return None
    
    # Group by category
    grouped = df.groupby(cat_col.name)[num_col.name]
    means = grouped.mean().sort_values(ascending=False)
    counts = grouped.count()
    
    if len(means) < 2:
        return None
    
    # Find category with high value but low count (hidden opportunity)
    for cat in means.index[:3]:
        mean_val = means[cat]
        count = counts[cat]
        total_mean = means.mean()
        
        if mean_val > total_mean * 1.2 and count < counts.median():
            insight = f"💎 Hidden gem: {cat} has {mean_val:.1f} average {num_col.name} but only {count} records — potential opportunity!"
            
            spec = generate_vega_spec(
                chart_type="bar",
                x=cat_col.name,
                y=num_col.name,
                title=f"{num_col.name} by {cat_col.name}",
                x_type="nominal",
                y_type="quantitative"
            )
            
            return {
                'insight': insight,
                'chart_type': 'bar',
                'x_column': cat_col.name,
                'y_column': num_col.name,
                'spec': spec
            }
    
    return None


def find_seasonal_pattern(profile: DatasetProfile, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """
    Detect seasonal or cyclical patterns in time series data.
    """
    temporal_cols = [c for c in profile.columns if c.dtype == 'temporal']
    numeric_cols = [c for c in profile.columns if c.dtype == 'numeric']
    
    if not temporal_cols or not numeric_cols:
        return None
    
    time_col = temporal_cols[0]
    num_col = numeric_cols[0]
    
    if time_col.name not in df.columns or num_col.name not in df.columns:
        return None
    
    try:
        df_sorted = df.sort_values(by=time_col.name).copy()
        df_sorted[time_col.name] = pd.to_datetime(df_sorted[time_col.name], errors='coerce')
        series = pd.to_numeric(df_sorted[num_col.name], errors='coerce')
        
        if len(series) < 12:  # Need enough data points
            return None
        
        # Extract month/quarter if possible
        df_sorted['month'] = df_sorted[time_col.name].dt.month
        df_sorted['quarter'] = df_sorted[time_col.name].dt.quarter
        
        # Check for seasonal patterns by month
        monthly_avg = df_sorted.groupby('month')[num_col.name].mean()
        if len(monthly_avg) >= 6:
            # Check for clear seasonal pattern (high variance between months)
            if monthly_avg.std() / monthly_avg.mean() > 0.2:
                peak_month = monthly_avg.idxmax()
                low_month = monthly_avg.idxmin()
                peak_val = monthly_avg.max()
                low_val = monthly_avg.min()
                
                if peak_val > low_val * 1.3:  # At least 30% difference
                    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                    insight = (
                        f"📅 Seasonal pattern detected: {num_col.name} peaks in {month_names[peak_month-1]} "
                        f"({peak_val:.1f}) and dips in {month_names[low_month-1]} ({low_val:.1f}) — "
                        f"consider seasonal planning!"
                    )
                    
                    spec = generate_vega_spec(
                        chart_type="line",
                        x=time_col.name,
                        y=num_col.name,
                        title=f"{num_col.name} - Seasonal Pattern",
                        x_type="temporal",
                        y_type="quantitative"
                    )
                    
                    return {
                        'insight': insight,
                        'chart_type': 'line',
                        'x_column': time_col.name,
                        'y_column': num_col.name,
                        'spec': spec
                    }
    except Exception as e:
        logger.debug(f"Seasonal pattern detection failed: {e}")
    
    return None


def find_clustering_pattern(profile: DatasetProfile, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """
    Detect natural clusters or groups in numeric data.
    """
    numeric_cols = [c for c in profile.columns if c.dtype == 'numeric']
    
    if len(numeric_cols) < 2:
        return None
    
    col1 = numeric_cols[0]
    col2 = numeric_cols[1] if len(numeric_cols) > 1 else None
    
    if col1.name not in df.columns:
        return None
    
    try:
        series = pd.to_numeric(df[col1.name], errors='coerce').dropna()
        
        if len(series) < 10:
            return None
        
        # Simple clustering detection using quartiles
        q1, q2, q3 = series.quantile([0.25, 0.5, 0.75])
        iqr = q3 - q1
        
        # Check if data forms distinct groups
        low_group = series[series <= q1]
        mid_group = series[(series > q1) & (series <= q3)]
        high_group = series[series > q3]
        
        # If groups are well-separated
        if (q2 - q1) > iqr * 0.5 and (q3 - q2) > iqr * 0.5:
            insight = (
                f"🔍 Natural clusters found in {col1.name}: "
                f"{len(low_group)} low values (≤{q1:.1f}), "
                f"{len(mid_group)} mid values ({q1:.1f}-{q3:.1f}), "
                f"{len(high_group)} high values (>{q3:.1f}) — distinct groups detected!"
            )
            
            spec = generate_vega_spec(
                chart_type="histogram",
                x=col1.name,
                title=f"Distribution of {col1.name} - Clustering Pattern",
                x_type="quantitative"
            )
            
            return {
                'insight': insight,
                'chart_type': 'histogram',
                'x_column': col1.name,
                'spec': spec
            }
    except Exception as e:
        logger.debug(f"Clustering detection failed: {e}")
    
    return None


def find_anomaly_score(profile: DatasetProfile, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """
    Score and identify the most anomalous records.
    """
    numeric_cols = [c for c in profile.columns if c.dtype == 'numeric']
    
    if not numeric_cols or len(df) < 10:
        return None
    
    try:
        # Calculate z-scores for numeric columns
        anomaly_scores = pd.Series(0.0, index=df.index)
        
        for col in numeric_cols[:3]:  # Check first 3 numeric columns
            if col.name not in df.columns:
                continue
            series = pd.to_numeric(df[col.name], errors='coerce')
            if series.std() > 0:
                z_scores = (series - series.mean()) / series.std()
                anomaly_scores += z_scores.abs()
        
        # Find most anomalous
        if anomaly_scores.max() > 3.0:  # 3+ standard deviations
            max_idx = anomaly_scores.idxmax()
            max_score = anomaly_scores.max()
            
            
            # Identify which column contributed most to the anomaly
            max_contrib_col = None
            max_contrib_score = 0
            culprit_value = None
            culprit_mean = 0
            culprit_std = 0
            
            # Find the most anomalous column for this row
            row_idx = max_idx
            for col in numeric_cols[:3]:
                 if col.name not in df.columns:
                    continue
                 series = pd.to_numeric(df[col.name], errors='coerce')
                 if series.std() > 0:
                    val = series.iloc[row_idx]
                    z = abs((val - series.mean()) / series.std())
                    if z > max_contrib_score:
                        max_contrib_score = z
                        max_contrib_col = col.name
                        culprit_value = val
                        culprit_mean = series.mean()
                        culprit_std = series.std()

            msg = (
                f"⚠️ Anomaly detected: Row {max_idx + 1} stands out significantly "
                f"(score: {max_score:.1f})"
            )
            
            # Get AI explanation if possible
            if max_contrib_col:
                # Get context from other columns
                row_data = df.iloc[row_idx].to_dict()
                explanation = explain_anomaly(
                    max_contrib_col,
                    culprit_value,
                    culprit_mean,
                    culprit_std,
                    row_data
                )
                if explanation:
                    msg += f"\n\n🤖 AI Analysis:\n{explanation}"
                else:
                    msg += " — worth investigating!"
            else:
                msg += " — worth investigating!"
                
            insight = msg
            
            # Create a chart highlighting the anomaly
            if len(numeric_cols) >= 2:
                spec = generate_vega_spec(
                    chart_type="scatter",
                    x=numeric_cols[0].name,
                    y=numeric_cols[1].name,
                    title=f"Data Points - Anomaly Highlighted",
                    x_type="quantitative",
                    y_type="quantitative"
                )
            else:
                # Single column anomaly - use a tick chart (1D scatter)
                spec = generate_vega_spec(
                    chart_type="tick",
                    x=numeric_cols[0].name,
                    title=f"Distribution of {numeric_cols[0].name} (Anomaly: {culprit_value})",
                    x_type="quantitative"
                )
                
            return {
                'insight': insight,
                'chart_type': 'scatter' if len(numeric_cols) >= 2 else 'tick',
                'x_column': numeric_cols[0].name,
                'y_column': numeric_cols[1].name if len(numeric_cols) >= 2 else None,
                'spec': spec
            }
    except Exception as e:
        logger.debug(f"Anomaly scoring failed: {e}")
    
    return None


def generate_surprise(profile: DatasetProfile, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """
    Generate a surprising insight and chart.
    
    Tries multiple discovery methods and returns the most interesting one.
    """
    discoveries = []
    
    # Try correlation discovery
    corr_result = find_surprising_correlation(profile, df)
    if corr_result:
        discoveries.append(('correlation', corr_result))
    
    # Try growth anomaly
    growth_result = find_growth_anomaly(profile, df)
    if growth_result:
        discoveries.append(('growth', growth_result))
    
    # Try hidden leader
    leader_result = find_hidden_leader(profile, df)
    if leader_result:
        discoveries.append(('leader', leader_result))
    
    # Try seasonal pattern
    seasonal_result = find_seasonal_pattern(profile, df)
    if seasonal_result:
        discoveries.append(('seasonal', seasonal_result))
    
    # Try clustering
    cluster_result = find_clustering_pattern(profile, df)
    if cluster_result:
        discoveries.append(('clustering', cluster_result))
    
    # Try anomaly scoring
    anomaly_result = find_anomaly_score(profile, df)
    if anomaly_result:
        discoveries.append(('anomaly', anomaly_result))
    
    if not discoveries:
        return None
    
    # Return most interesting discovery (prioritize correlations, then seasonal, then growth)
    priority_order = {'correlation': 0, 'seasonal': 1, 'growth': 2, 'clustering': 3, 'anomaly': 4, 'leader': 5}
    discoveries.sort(key=lambda x: priority_order.get(x[0], 99))
    return discoveries[0][1]

