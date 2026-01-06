"""
AI-powered insights service using Groq (primary) and Gemini (fallback).

This module provides AI-generated insights for data analysis
with automatic failover between providers.
"""
import os
import json
import hashlib
import logging
import time
from typing import Dict, Any, List, Optional
from groq import Groq
from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Provider clients (singletons)
_groq_client: Optional[Groq] = None
_gemini_model = None  # Lazy loaded to avoid import if not needed

# AI insight cache (in-memory with TTL)
_insight_cache: Dict[str, Dict[str, Any]] = {}
INSIGHT_CACHE_TTL_SECONDS = 1800  # 30 minutes


def sanitize_for_prompt(text: str, max_length: int = 100) -> str:
    """
    Sanitize user-provided text before including in AI prompts.
    
    Prevents prompt injection by:
    - Removing control characters and newlines
    - Limiting length
    - Escaping potential instruction patterns
    """
    if not text:
        return ""
    
    # Remove newlines, tabs, and control characters
    sanitized = ''.join(char for char in text if char.isprintable() and char not in '\n\r\t')
    
    # Limit length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."
    
    # Escape patterns that might look like instructions
    dangerous_patterns = ['SYSTEM:', 'USER:', 'ASSISTANT:', 'IGNORE', 'FORGET', 'NEW INSTRUCTION']
    for pattern in dangerous_patterns:
        sanitized = sanitized.replace(pattern, f'[{pattern}]')
    
    return sanitized


def get_groq_client() -> Optional[Groq]:
    """Get or create Groq client singleton."""
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if api_key:
            _groq_client = Groq(api_key=api_key)
            logger.info("Groq AI client initialized")
    return _groq_client


def get_gemini_model():
    """Get or create Gemini model singleton."""
    global _gemini_model
    if _gemini_model is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                settings = get_settings()
                _gemini_model = genai.GenerativeModel(settings.gemini_model)
                logger.info(f"Gemini AI fallback initialized with model: {settings.gemini_model}")
            except Exception as e:
                logger.warning(f"Gemini initialization failed: {e}")
    return _gemini_model


def _call_groq(prompt: str, system_prompt: str, max_tokens: int = 300) -> Optional[str]:
    """Call Groq API."""
    client = get_groq_client()
    if not client:
        return None
    
    settings = get_settings()
    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        max_tokens=max_tokens,
        temperature=0.3,
        timeout=15.0  # 15s timeout to prevent hanging
    )
    return response.choices[0].message.content


def _call_gemini(prompt: str, system_prompt: str) -> Optional[str]:
    """Call Gemini API (fallback)."""
    model = get_gemini_model()
    if not model:
        return None
    
    full_prompt = f"{system_prompt}\n\n{prompt}"
    try:
        # Attempt to use timeout (supported in newer library versions)
        response = model.generate_content(
            full_prompt, 
            request_options={"timeout": 15}
        )
        return response.text
    except TypeError:
        # Fallback for older library versions (no timeout)
        logger.warning("Gemini timeout config not supported, proceeding without timeout")
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        logger.error(f"Gemini generation failed: {e}")
        return None


def _call_ai_with_fallback(prompt: str, system_prompt: str, max_tokens: int = 300) -> Optional[str]:
    """
    Call AI with automatic fallback.
    
    Order: Groq -> Gemini -> None
    """
    # Try Groq first
    try:
        result = _call_groq(prompt, system_prompt, max_tokens)
        if result:
            logger.debug("AI response from Groq")
            return result
    except Exception as e:
        error_str = str(e).lower()
        if "rate" in error_str or "limit" in error_str or "429" in error_str:
            logger.warning(f"Groq rate limited, trying Gemini fallback: {e}")
        else:
            logger.warning(f"Groq error, trying fallback: {e}")
    
    # Fallback to Gemini
    try:
        result = _call_gemini(prompt, system_prompt)
        if result:
            logger.info("AI response from Gemini (fallback)")
            return result
    except Exception as e:
        logger.error(f"Gemini fallback also failed: {e}")
    
    return None


def generate_ai_insights(
    data_summary: Dict[str, Any],
    chart_type: str,
    column_profiles: List[Dict[str, Any]],
    x_column: str = None,
    y_column: str = None
) -> Optional[str]:
    """
    Generate AI-powered insights for a specific chart.
    The insights are tailored to the chart type and columns being visualized.
    Results are cached to reduce redundant API calls.
    """
    # Generate cache key from inputs
    cache_key_data = {
        "chart_type": chart_type,
        "x_column": x_column,
        "y_column": y_column,
        "row_count": data_summary.get("row_count"),
        "col_count": data_summary.get("column_count"),
    }
    cache_key = hashlib.md5(json.dumps(cache_key_data, sort_keys=True).encode()).hexdigest()
    
    # Check cache
    if cache_key in _insight_cache:
        cached = _insight_cache[cache_key]
        if time.time() - cached["timestamp"] < INSIGHT_CACHE_TTL_SECONDS:
            logger.debug(f"Returning cached AI insight for {chart_type}")
            return cached["result"]
        else:
            # Expired, remove from cache
            del _insight_cache[cache_key]
    
    # Check if any AI is available
    if not get_groq_client() and not get_gemini_model():
        logger.debug("No AI providers configured (set GROQ_API_KEY or GEMINI_API_KEY)")
        return None
    
    # Sanitize column names
    safe_x = sanitize_for_prompt(x_column, 50) if x_column else "category"
    safe_y = sanitize_for_prompt(y_column, 50) if y_column else "count"
    
    # Build context about the columns being charted
    x_col_info = next((col for col in column_profiles if col['name'] == x_column), None)
    y_col_info = next((col for col in column_profiles if col['name'] == y_column), None) if y_column else None
    
    col_context = f"X-axis: {safe_x}"
    if x_col_info:
        col_context += f" ({x_col_info['dtype']}, {x_col_info.get('unique_count', '?')} unique values)"
    if y_column and y_col_info:
        col_context += f"\nY-axis: {safe_y} ({y_col_info['dtype']})"
    
    # Chart-specific prompts
    chart_prompts = {
        "bar": f"Bar chart of '{safe_x}'. Key patterns?",
        "donut": f"Pie chart of '{safe_x}'. Largest segments?",
        "line": f"Line: '{safe_y}' over '{safe_x}'. Trends?",
        "scatter": f"Scatter: '{safe_x}' vs '{safe_y}'. Correlation?",
        "histogram": f"Histogram of '{safe_x}'. Distribution shape?",
        "heatmap": f"Heatmap of '{safe_x}' x '{safe_y}'. Hotspots?",
    }
    
    chart_context = chart_prompts.get(chart_type, f"{chart_type} of '{safe_x}'")
    
    prompt = f"""Give 2 bullet-point insights for this chart.
{chart_type.upper()}: {data_summary.get('row_count', 0)} rows. {col_context}
{chart_context}
Be specific. Plain text only."""

    result = _call_ai_with_fallback(
        prompt, 
        "Data analyst. Concise insights only.",
        max_tokens=150  # Reduced from 250
    )
    
    if result:
        # Clean up the result for better display
        result = _format_ai_response(result)
        logger.info("Chart-specific AI insight generated successfully")
        
        # Cache the result
        _insight_cache[cache_key] = {
            "result": result,
            "timestamp": time.time()
        }
        
    return result


def _format_ai_response(text: str) -> str:
    """Clean and format AI response for display."""
    if not text:
        return text
    
    # Remove markdown bolding and italics to reduce visual noise (asterisks)
    clean_text = text.replace('**', '').replace('__', '').replace('*', '')
    
    # Remove excessive newlines
    lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
    
    # Ensure bullet points are consistent
    formatted_lines = []
    for line in lines:
        # Skip meta-text like "Here are the insights:"
        if any(skip in line.lower() for skip in ['here are', 'based on', 'insights:', 'analysis:']):
            continue
            
        # Clean leading symbols
        cleaned_line = line
        if line.startswith(('-', '•')):
             cleaned_line = line[1:].strip()
             
        # Add consistent bullet
        formatted_lines.append(f"• {cleaned_line}")
    
    return '\n'.join(formatted_lines[:4])


def generate_chart_recommendation(
    column_profiles: List[Dict[str, Any]],
    row_count: int
) -> Optional[Dict[str, str]]:
    """Get AI recommendation for the best chart type."""
    if not get_groq_client() and not get_gemini_model():
        return None
    
    columns_desc = ", ".join([
        f"{col['name']} ({col['dtype']})"
        for col in column_profiles[:8]
    ])
    
    prompt = f"""Given this dataset, what's the single best chart to visualize it?

Rows: {row_count}
Columns: {columns_desc}

Reply in EXACTLY this format (no other text):
CHART: [bar/line/scatter/area/heatmap/donut/histogram]
REASON: [One sentence explanation]"""

    content = _call_ai_with_fallback(
        prompt,
        "You are a data visualization expert. Reply only in the exact format requested.",
        max_tokens=100
    )
    
    if not content:
        return None
    
    lines = content.strip().split('\n')
    result = {}
    for line in lines:
        if line.startswith('CHART:'):
            result['chart_type'] = line.replace('CHART:', '').strip().lower()
        elif line.startswith('REASON:'):
            result['reason'] = line.replace('REASON:', '').strip()
    
    if 'chart_type' in result and 'reason' in result:
        return result
    return None


def summarize_survey_responses(
    question: str,
    responses: List[str],
    max_responses: int = 50
) -> Optional[str]:
    """Summarize open-ended survey responses using AI."""
    if not get_groq_client() and not get_gemini_model():
        return None
    
    sample = responses[:max_responses]
    responses_text = "\n".join([f"- {r[:200]}" for r in sample])
    
    prompt = f"""Summarize the key themes from these {len(sample)} survey responses to: "{question}"

Responses:
{responses_text}

Provide a 2-3 sentence summary of the main themes. Be specific about what respondents think."""

    return _call_ai_with_fallback(
        prompt,
        "You are a survey analyst. Summarize themes concisely.",
        max_tokens=200
    )


def analyze_column(
    column_name: str,
    dtype: str,
    sample_values: List[str],
    unique_count: int,
    null_count: int
) -> str:
    """
    Generate AI analysis for a single column.
    Falls back to rule-based description if AI unavailable.
    """
    # Rule-based fallback
    fallback = f"{column_name}: {dtype} column with {unique_count} unique values"
    if null_count > 0:
        fallback += f" ({null_count} missing)"
    
    if not get_groq_client() and not get_gemini_model():
        return fallback
    
    samples = ", ".join([str(v)[:50] for v in sample_values[:5]])
    prompt = f"""Describe this data column in ONE sentence:

Column: {sanitize_for_prompt(column_name, 60)}
Type: {dtype}
Unique values: {unique_count}
Missing values: {null_count}
Sample values: {samples}

What does this column represent? Be specific and concise."""

    result = _call_ai_with_fallback(prompt, "You are a data analyst. Describe columns concisely.", max_tokens=100)
    return result if result else fallback


def detect_outliers(
    column_name: str,
    values: List[Any],
    dtype: str
) -> Optional[str]:
    """
    Detect outliers in a column using AI.
    Falls back to statistical detection for numeric columns.
    """
    # Rule-based fallback for numeric columns
    if dtype == "numeric" and values:
        try:
            nums = [float(v) for v in values if v is not None]
            if nums:
                mean_val = sum(nums) / len(nums)
                std_val = (sum((x - mean_val) ** 2 for x in nums) / len(nums)) ** 0.5
                outliers = [v for v in nums if abs(v - mean_val) > 3 * std_val]
                if outliers:
                    return f"Found {len(outliers)} potential outliers (>3σ from mean)"
        except:
            pass
    
    if not get_groq_client() and not get_gemini_model():
        return None
    
    sample = [str(v)[:30] for v in values[:20]]
    prompt = f"""Analyze these values for outliers or anomalies:

Column: {sanitize_for_prompt(column_name, 40)}
Values: {', '.join(sample)}

If you spot any outliers or unusual values, describe them in ONE sentence. If none, say "No obvious outliers"."""

    return _call_ai_with_fallback(prompt, "You are a data quality analyst.", max_tokens=100)


def suggest_data_cleaning(
    column_profiles: List[Dict[str, Any]],
    row_count: int
) -> List[str]:
    """
    Suggest data cleaning actions using AI.
    Falls back to rule-based suggestions.
    """
    suggestions = []
    
    # Rule-based suggestions (always available) - more actionable wording
    for col in column_profiles:
        null_pct = (col.get('null_count', 0) / row_count * 100) if row_count > 0 else 0
        if null_pct > 20:
            suggestions.append(f"⚠️ **High missing data**: '{col['name']}' has {null_pct:.0f}% missing values. Consider filling with mean/mode or removing rows.")
        elif null_pct > 0:
            suggestions.append(f"📝 '{col['name']}' has {col.get('null_count', 0)} missing values ({null_pct:.1f}%)")
        if col.get('unique_count', 0) == row_count and col['dtype'] == 'nominal':
            suggestions.append(f"� '{col['name']}' is likely an ID column (all values unique)")
        if col.get('unique_count', 0) == 1:
            suggestions.append(f"⚡ '{col['name']}' has only 1 unique value - consider removing (no variation)")
    
    if not get_groq_client() and not get_gemini_model():
        return suggestions[:5] if suggestions else ["✅ Data looks clean - no obvious issues found"]
    
    # AI-enhanced suggestions
    cols_desc = "\n".join([
        f"- {sanitize_for_prompt(c['name'], 40)}: {c['dtype']}, {c.get('unique_count', '?')} unique, {c.get('null_count', 0)} nulls"
        for c in column_profiles[:15]
    ])
    
    prompt = f"""Review this dataset structure and suggest 2 specific data cleaning improvements:

Dataset: {row_count} rows
Columns:
{cols_desc}

For each suggestion:
1. Start with what the issue is
2. Explain why it matters  
3. Suggest a specific fix

Keep each suggestion to 1-2 sentences. Use plain text, no markdown."""

    ai_result = _call_ai_with_fallback(prompt, "You are a data quality expert.", max_tokens=250)
    if ai_result:
        # Format the AI response
        formatted = _format_ai_response(ai_result)
        # Add as a single insight block, not multiple unformatted lines
        suggestions.insert(0, "🤖 " + formatted.replace('\n', '\n   '))
        
    return suggestions


def generate_narrative_report(
    data_summary: Dict[str, Any],
    column_profiles: List[Dict[str, Any]],
    charts_context: List[str]
) -> str:
    """
    Generate a detailed, humanized narrative report.
    """
    if not get_groq_client() and not get_gemini_model():
        return "## Error\nAI services are not configured."

    # Summarize columns
    cols_desc = "\n".join([
        f"- {c['name']} ({c['dtype']})" for c in column_profiles[:20]
    ])
    
    # Charts availability
    charts_list = "\n".join([f"Chart {i}: {desc}" for i, desc in enumerate(charts_context)])
    
    prompt = f"""Write a detailed, engaging business report for this dataset.
    
CONTEXT:
Dataset: {data_summary.get('row_count')} rows, {data_summary.get('column_count')} columns.
Key Columns:
{cols_desc}

Visuals Available:
{charts_list}

INSTRUCTIONS:
1. **Tone**: You are a senior analyst speaking to a non-technical client. Be conversational, direct, and human. 
   - DO NOT use words like "leverage", "utilize", "pivotal", "delve", "showcase".
   - DO NOT say "The dataset contains...". Say "We looked at..." or "The data shows...".
   - Make it sound like a story.

2. **Structure**:
   # Executive Summary
   (2-3 paragraphs. High level impact.)
   
   # Key Trends & Analysis
   (Detailed breakdown. Group related findings.)
   
   # Recommendations
   (Actionable next steps.)

3. **Embed Charts**: 
   - You MUST insert `{{{{CHART_0}}}}`, `{{{{CHART_1}}}}` etc. where they fit best in the narrative.
   - Don't just list them. Discuss the finding, then show the chart.

Write the full report in Markdown."""

    return _call_ai_with_fallback(
        prompt, 
        "You are a human business analyst. Write naturally.", 
        max_tokens=2000
    ) or "## Report Generation Failed\nCould not generate report."
    
    return suggestions[:6] if suggestions else ["✅ Data quality looks good - no issues detected"]


def generate_comprehensive_analysis(
    profile_dict: Dict[str, Any],
    sample_data: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Generate a comprehensive AI analysis of the entire dataset.
    Returns structured results with fallbacks.
    """
    result = {
        "summary": None,
        "column_insights": [],
        "cleaning_suggestions": [],
        "key_findings": []
    }
    
    row_count = profile_dict.get('row_count', 0)
    column_count = profile_dict.get('column_count', 0)
    columns = profile_dict.get('columns', [])
    
    # 1. Overall Summary
    result["summary"] = f"Dataset with {row_count} rows and {column_count} columns"
    
    # 2. Column Insights (AI or fallback)
    for col in columns[:10]:  # Limit to 10 columns for performance
        col_samples = [row.get(col['name']) for row in sample_data[:5] if col['name'] in row]
        insight = analyze_column(
            col['name'],
            col['dtype'],
            col_samples,
            col.get('unique_count', 0),
            col.get('null_count', 0)
        )
        result["column_insights"].append({
            "column": col['name'],
            "insight": insight
        })
    
    # 3. Cleaning Suggestions
    result["cleaning_suggestions"] = suggest_data_cleaning(columns, row_count)
    
    # 4. Key Findings (AI)
    if get_groq_client() or get_gemini_model():
        cols_summary = ", ".join([f"{c['name']} ({c['dtype']})" for c in columns[:8]])
        prompt = f"""What are the 3 most interesting things about this dataset?

Dataset: {row_count} rows, {column_count} columns
Columns: {cols_summary}

List 3 brief, specific findings. No markdown."""

        findings = _call_ai_with_fallback(prompt, "You are a data scientist.", max_tokens=200)
        if findings:
            result["key_findings"] = [f.strip() for f in findings.split('\n') if f.strip()]
    
    return result


def generate_ai_chart_title(
    chart_type: str,
    x_column: str,
    y_column: str,
    data_sample: List[Dict[str, Any]] = None
) -> Optional[str]:
    """
    Generate a compelling, insight-driven chart title using AI.
    Example: "Electronics Dominates Sales (45%)" instead of "Sales by Category"
    """
    if not get_groq_client() and not get_gemini_model():
        return None
        
    # Sanitize inputs
    safe_x = sanitize_for_prompt(x_column, 50)
    safe_y = sanitize_for_prompt(y_column, 50) if y_column else "Count"
    
    # Format sample data for context
    sample_text = ""
    if data_sample:
        # Take up to 5 simple records
        simple_sample = []
        for row in data_sample[:5]:
            # Only keep relevant columns to save tokens
            clean_row = {k: v for k, v in row.items() if k in [x_column, y_column]}
            simple_sample.append(str(clean_row))
        sample_text = "\nSample Data: " + ", ".join(simple_sample)

    prompt = f"""Generate a short, insight-driven title (max 8 words) for this chart.
    
Chart: {chart_type}
X-axis: {safe_x}
Y-axis: {safe_y}
{sample_text}

Rules:
1. Don't use generic format like "X vs Y" or "Distribution of X"
2. Highlight the key story/finding if visible in sample
3. Use plain text, no markdown, no quotes
4. Example: "Sales Peaked in Q4" or "West Region Leads Revenue"
"""

    title = _call_ai_with_fallback(
        prompt, 
        "You are a data storyteller. Write punchy, journalistic chart titles.",
        max_tokens=20
    )
    
    if title:
        # Clean up
        title = title.strip().strip('"').strip("'")
        return title
        
    return None


def explain_anomaly(
    column_name: str,
    value: Any,
    mean: float,
    std_dev: float,
    row_context: Dict[str, Any] = None
) -> Optional[str]:
    """
    Generate an AI explanation for why a value is an outlier.
    """
    if not get_groq_client() and not get_gemini_model():
        return None
        
    context_str = ""
    if row_context:
        # Include other column values to give context (e.g., "Region: West")
        context_items = [f"{k}: {v}" for k, v in row_context.items() if k != column_name]
        if context_items:
            context_str = "\nContext: " + ", ".join(context_items[:5])

    z_score = (value - mean) / std_dev if std_dev > 0 else 0
    direction = "above" if value > mean else "below"
    
    prompt = f"""Explain this specific outlier in the '{column_name}' column.

Value: {value}
Average: {mean:.2f} (It is {abs(z_score):.1f} standard deviations {direction} average)
{context_str}

Provide 3 possible reasons for this anomaly in bullet points.
Be specific to the data domain (infer from column name).
Example reasons: "Holiday season spike", "Data entry error", "VIP customer transaction"
"""

    explanation = _call_ai_with_fallback(
        prompt, 
        "You are a data detective explaining anomalies. Be creative but grounded.",
        max_tokens=150
    )
    
    if explanation:
        return _format_ai_response(explanation)
        
    return None


def generate_executive_summary(
    profile: Dict[str, Any],
    sample_data: List[Dict[str, Any]]
) -> Optional[str]:
    """
    Generate a high-level executive summary of the dataset.
    Returns: Markdown formatted string
    """
    if not get_groq_client() and not get_gemini_model():
        return None

    # Prepare context
    row_count = profile.get('row_count', 0)
    col_count = profile.get('col_count', 0)
    cols =  profile.get('columns', [])
    
    col_summary = "\n".join([
        f"- {sanitize_for_prompt(c['name'], 40)} ({c['dtype']}): {c.get('unique_count', '?')} unique"
        for c in cols[:15]
    ])
    
    # Prepare sample data string
    data_str = ""
    if sample_data:
        data_str = "\nSample Data (first 3 rows):\n" + "\n".join([str(row) for row in sample_data[:3]])

    prompt = f"""Act as a Lead Data Analyst. Write a brief Executive Summary for this dataset.

Dataset Overview:
- {row_count} rows, {col_count} columns
- Columns:
{col_summary}
{data_str}

Format the output in Markdown exactly like this:
## 📊 Executive Summary
[1-2 sentences overview of what this data represents]

## 🔑 Key Findings
1. [Key finding 1 - trend, pattern, or dominant category]
2. [Key finding 2 - outlier or anomaly]
3. [Key finding 3 - interesting correlation or observation]

## 💡 Recommendations
1. [Actionable recommendation 1]
2. [Actionable recommendation 2]

Rules:
- Be professional, concise, and specific.
- Cite actual values/names from columns if possible.
- Do NOT use generic phrases like "The dataset contains..."
- If data is Sales/Time-series, mention growth/decline.
- Use plain text for emphasis. Do NOT use bolding or italics (avoids visual clutter).
"""

    summary = _call_ai_with_fallback(
        prompt, 
        "You are a senior data analyst writing for a CEO.",
        max_tokens=400
    )
    
    return summary


def recommend_chart_type_with_ai(
    profile: Dict[str, Any],
    sample_data: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Use AI to analyze the dataset structure and recommend the best visualization.
    Refines the heuristic recommendation with understanding of data content.
    """
    if not get_groq_client() and not get_gemini_model():
        return None
        
    cols_desc = "\n".join([
        f"- {sanitize_for_prompt(c['name'], 40)} ({c['dtype']}): {c.get('unique_count', '?')} unique"
        for c in profile.get('columns', [])[:8]
    ])
    
    # Prepare sample context
    sample_str = ""
    if sample_data:
        sample_str = "\nSample Data (rows):\n" + "\n".join([str(row) for row in sample_data[:3]])
        
    prompt = f"""Analyze this dataset and recommend the single best chart type.
    
Dataset: {profile.get('row_count', 0)} rows
Columns:
{cols_desc}
{sample_str}

Supported Charts: [bar, line, scatter, area, donut, histogram, heatmap]

Reply in JSON format:
{{
  "chart_type": "chart_type_name",
  "x_column": "column_name",
  "y_column": "column_name",
  "reason": "One sentence explanation",
  "confidence": 0.0 to 1.0
}}
"""

    response = _call_ai_with_fallback(
        prompt,
        "You are a data visualization expert. Reply in valid JSON only.",
        max_tokens=150
    )
    
    if response:
        try:
            # Basic cleanup of markdown code blocks often returned by LLMs
            json_str = response.replace('```json', '').replace('```', '').strip()
            import json
            result = json.loads(json_str)
            return result
        except Exception as e:
            logger.warning(f"Failed to parse AI chart recommendation: {e}")
            
    return None


def generate_predictive_insights(
    df_profile: Dict[str, Any],
    time_col: str,
    value_col: str,
    sample_data: List[Dict[str, Any]]
) -> Optional[str]:
    """
    Generate predictive insights for time-series data.
    """
    if not get_groq_client() and not get_gemini_model():
        return None
        
    # Isolate relevant data from sample for prompt
    data_points = []
    for row in sample_data[-10:]: # Use last 10 points for context
        if time_col in row and value_col in row:
            data_points.append(f"{row[time_col]}: {row[value_col]}")
            
    if not data_points:
        return None
        
    data_str = ", ".join(data_points)
    
    prompt = f"""Analyze this time-series data trend:
    
Column: '{value_col}' over '{time_col}'
Recent Data Points: {data_str}

Predict the short-term trend in 1-2 sentences. 
Mention the direction (growth/decline) and potential next values if the pattern holds.
Be cautious but insightful.
"""

    return _call_ai_with_fallback(
        prompt,
        "You are a forecasting analyst. Be concise.",
        max_tokens=100
    )


def generate_chart_annotations(
    chart_type: str,
    x_col: str, 
    y_col: str,
    sample_data: List[Dict[str, Any]]
) -> List[Dict[str, str]]:
    """
    Identify 1-2 key data points to annotate on the chart.
    """
    if not get_groq_client() and not get_gemini_model():
        return []

    # Simplify sample for prompt
    sample_str = str(sample_data[:8])
    
    prompt = f"""Identify 1 key data point to annotate on this {chart_type} chart.
    it should be a peak, trough, or outlier.

    Data: {sample_str}
    X: {x_col}, Y: {y_col}

    Reply in JSON:
    [
      {{
        "x_value": "exact value from x column",
        "y_value": "exact value from y column", 
        "text": "Short annotation text (e.g. 'Peak Sales')"
      }}
    ]
    """
    
    response = _call_ai_with_fallback(
        prompt,
        "You are a data annotator. Reply in JSON only.",
        max_tokens=150
    )
    
    if response:
         try:
            json_str = response.replace('```json', '').replace('```', '').strip()
            import json
            result = json.loads(json_str)
            if isinstance(result, list):
                return result
         except:
             pass
             
    return []


def analyze_dataset_structure(
    profile: Dict[str, Any],
    sample_data: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Use AI to understand the dataset structure and group columns into logical sections.
    This drives the dashboard layout.
    """
    if not get_groq_client() and not get_gemini_model():
        return None

    # Prepare context
    cols_desc = "\n".join([
        f"- {sanitize_for_prompt(c['name'], 50)} ({c['dtype']}): {c.get('unique_count', '?')} unique"
        for c in profile.get('columns', [])[:50]
    ])
    
    sample_rows = ""
    if sample_data:
        # Simplified samples
        sample_rows = "\nSample Data:\n" + "\n".join([
            str({k: v for k, v in row.items() if k in [c['name'] for c in profile.get('columns', [])[:10]]})
            for row in sample_data[:2]
        ])

    prompt = f"""Analyze this dataset structure and help me organize a dashboard.
    
Dataset Columns:
{cols_desc}
{sample_rows}

Task: Group these columns into logical sections to unclutter the view.
1. Identify "Grid/Matrix" questions (e.g., related rating scales) and group them.
2. Identify "Demographics" (Age, Gender, Region).
3. Identify "Performance Metrics".

Reply in JSON format:
{{
  "sections": [
    {{
      "title": "Section Title (e.g., 'Respondent Profile')",
      "columns": ["col1", "col2"],
      "type": "standard"  // or "grid" if it's a Likert/Matrix group coverage
    }}
  ]
}}
"""

    response = _call_ai_with_fallback(
        prompt,
        "You are a data architect. Output valid JSON only.",
        max_tokens=600
    )
    
    if response:
        try:
            # Clean markdown
            json_str = response.replace('```json', '').replace('```', '').strip()
            return json.loads(json_str)
        except Exception as e:
            logger.warning(f"Failed to parse AI structure analysis: {e}")
            
    return None
