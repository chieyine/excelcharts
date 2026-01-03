"""
Story Mode - Generate one-page PDF reports with insights and charts.
"""
import logging
from typing import List, Dict, Any
from app.core.schemas import DatasetProfile, ChartCandidate

logger = logging.getLogger(__name__)


def generate_story_title(profile: DatasetProfile, filename: str) -> str:
    """
    Generate an intelligent title for the story.
    """
    # Extract meaningful name from filename
    base_name = filename.replace('.csv', '').replace('.xlsx', '').replace('.xls', '')
    base_name = base_name.replace('_', ' ').replace('-', ' ').title()
    
    # Add context based on data
    if profile.row_count > 1000:
        return f"{base_name} - Data Analysis Report"
    else:
        return f"{base_name} - Insights & Trends"


def generate_executive_summary(
    profile: DatasetProfile,
    insights: List[str],
    recommended_chart: ChartCandidate
) -> str:
    """
    Generate executive summary paragraph.
    """
    summary_parts = [
        f"This report analyzes {profile.row_count:,} data points across {profile.col_count} dimensions."
    ]
    
    if insights:
        summary_parts.append(f"Key findings include: {insights[0].lower()}")
        if len(insights) > 1:
            summary_parts.append(f"Additionally, {insights[1].lower()}")
    
    summary_parts.append(
        f"The recommended visualization is a {recommended_chart.chart_type} chart "
        f"showing {recommended_chart.title.lower()}."
    )
    
    return " ".join(summary_parts)


def generate_story(
    profile: DatasetProfile,
    recommended_chart: ChartCandidate,
    alternatives: List[ChartCandidate],
    insights: List[str],
    filename: str
) -> Dict[str, Any]:
    """
    Generate a complete story structure for PDF export.
    
    Returns:
        Dict with title, summary, insights, charts, and conclusion
    """
    title = generate_story_title(profile, filename)
    summary = generate_executive_summary(profile, insights, recommended_chart)
    
    # Select 2-3 best charts (recommended + top alternatives)
    charts = [recommended_chart] + alternatives[:2]
    
    # Generate conclusion
    conclusion = (
        f"Based on the analysis of {profile.row_count:,} records, "
        f"the data reveals important patterns and trends. "
        f"The visualizations above highlight the key relationships and insights. "
        f"Consider these findings when making data-driven decisions."
    )
    
    return {
        'title': title,
        'summary': summary,
        'insights': insights[:3],  # Top 3 insights
        'charts': [
            {
                'title': c.title,
                'description': c.description,
                'chart_type': c.chart_type
            }
            for c in charts
        ],
        'conclusion': conclusion,
        'metadata': {
            'row_count': profile.row_count,
            'col_count': profile.col_count,
            'filename': filename
        }
    }
