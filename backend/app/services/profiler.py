import logging
import re
import pandas as pd
import numpy as np
from app.core.schemas import ColumnProfile, DatasetProfile
from app.core.performance import track_performance
from pandas.api.types import is_numeric_dtype, is_datetime64_any_dtype
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)

# Keywords for detecting Likert scale polarity
# Ordered from most negative (-2) to most positive (+2)
POLARITY_KEYWORDS = {
    # Strong negative (-2)
    "strongly disagree": -2, "very dissatisfied": -2, "very unlikely": -2,
    "very poor": -2, "never": -2, "not at all": -2, "extremely dissatisfied": -2,
    "completely disagree": -2, "totally disagree": -2,
    
    # Negative (-1)
    "disagree": -1, "dissatisfied": -1, "unlikely": -1, "poor": -1,
    "rarely": -1, "seldom": -1, "bad": -1, "no": -1, "false": -1,
    
    # Neutral (0)
    "neutral": 0, "neither": 0, "sometimes": 0, "average": 0,
    "moderate": 0, "uncertain": 0, "undecided": 0, "don't know": 0,
    "i don't know": 0, "not sure": 0, "maybe": 0, "fair": 0,
    
    # Positive (+1)
    "agree": 1, "satisfied": 1, "likely": 1, "good": 1,
    "often": 1, "usually": 1, "yes": 1, "true": 1,
    
    # Strong positive (+2)
    "strongly agree": 2, "very satisfied": 2, "very likely": 2,
    "excellent": 2, "always": 2, "very good": 2, "extremely satisfied": 2,
    "completely agree": 2, "totally agree": 2,
}


def extract_numeric_prefix(value: str) -> Optional[int]:
    """
    Extract numeric prefix from values like "1 (Strongly Disagree)" or "2. Disagree".
    Returns the number or None if no prefix found.
    """
    if not isinstance(value, str):
        return None
    
    # Match patterns like "1 (Label)", "1. Label", "1 - Label", "1: Label"
    match = re.match(r'^(\d+)\s*[\(\.\-:\s]', value.strip())
    if match:
        return int(match.group(1))
    
    # Also match just numbers
    if value.strip().isdigit():
        return int(value.strip())
    
    return None


def get_polarity_score(value: str) -> Optional[float]:
    """
    Get polarity score for a Likert value based on keywords.
    Returns score from -2 (most negative) to +2 (most positive), or None if unknown.
    """
    if not isinstance(value, str):
        return None
    
    value_lower = value.lower().strip()
    
    # Check for exact matches first
    if value_lower in POLARITY_KEYWORDS:
        return POLARITY_KEYWORDS[value_lower]
    
    # Check for partial matches (keywords contained in value)
    for keyword, score in POLARITY_KEYWORDS.items():
        if keyword in value_lower:
            return score
    
    return None


def detect_likert_scale(unique_values: List[str]) -> Tuple[bool, Optional[List[str]]]:
    """
    Universal Likert scale detection that works for ANY scale options.
    
    Detection strategy:
    1. Check for numeric prefixes (1, 2, 3...) and sort by number
    2. Check for polarity keywords and sort by sentiment
    3. Must have 2-10 unique values (typical Likert range)
    
    Returns (is_likert, ordered_values).
    """
    if not unique_values or len(unique_values) < 2 or len(unique_values) > 10:
        return False, None
    
    # Clean and filter values
    clean_values = [str(v).strip() for v in unique_values if v is not None and str(v).strip()]
    
    if len(clean_values) < 2:
        return False, None
    
    # Strategy 1: Check for numeric prefixes
    numeric_scores = []
    for val in clean_values:
        num = extract_numeric_prefix(val)
        if num is not None:
            numeric_scores.append((val, num))
    
    # If most values have numeric prefixes, sort by number
    if len(numeric_scores) >= len(clean_values) * 0.6:
        sorted_vals = sorted(numeric_scores, key=lambda x: x[1])
        return True, [v[0] for v in sorted_vals]
    
    # Strategy 2: Check for polarity keywords
    polarity_scores = []
    for val in clean_values:
        score = get_polarity_score(val)
        if score is not None:
            polarity_scores.append((val, score))
    
    # If most values have polarity keywords, it's likely Likert
    if len(polarity_scores) >= len(clean_values) * 0.5:
        # Sort from most negative to most positive (standard survey display)
        sorted_vals = sorted(polarity_scores, key=lambda x: x[1])
        return True, [v[0] for v in sorted_vals]
    
    # Strategy 3: Check if it's a simple Yes/No/Maybe type scale
    simple_scales = [
        {"yes", "no"},
        {"yes", "no", "maybe"},
        {"true", "false"},
        {"true", "false", "i don't know"},
    ]
    normalized = set(v.lower().strip() for v in clean_values)
    for scale in simple_scales:
        if normalized == scale or normalized.issubset(scale):
            # Return in standard order
            if "yes" in normalized:
                order = ["Yes", "Maybe", "No"] if "maybe" in normalized else ["Yes", "No"]
            elif "true" in normalized:
                order = ["True", "False", "I don't know"] if "i don't know" in normalized else ["True", "False"]
            else:
                order = clean_values
            # Match case to original values
            result = []
            for o in order:
                for v in clean_values:
                    if v.lower() == o.lower():
                        result.append(v)
                        break
            return True, result if result else clean_values
    
    return False, None


def detect_checkbox_column(series: pd.Series) -> bool:
    """
    Detect if column contains checkbox/multi-select data (comma-separated values).
    Google Forms exports checkboxes as "Option A, Option B, Option C".
    
    Detection strategies:
    1. Check if values contain commas with multiple parts
    2. Check for very high unique count (combinations create many unique values)
    3. Check if unique values share common substrings (individual options appear in combos)
    """
    sample = series.dropna().head(200)  # Larger sample for better detection
    if sample.empty:
        return False
    
    unique_count = series.nunique()
    row_count = len(series.dropna())
    
    # Strategy 1: Check for comma-separated values
    comma_count = 0
    all_parts = set()
    for val in sample:
        if isinstance(val, str) and ',' in val:
            parts = [p.strip() for p in val.split(',')]
            valid_parts = [p for p in parts if p]
            if len(valid_parts) >= 2:
                comma_count += 1
                all_parts.update(valid_parts)
    
    # If even 10% of values have comma-separated content, likely checkbox
    if len(sample) > 0 and comma_count / len(sample) > 0.10:
        return True
    
    # Strategy 2: High unique count suggests combinations
    # If unique values >> expected options (say 20+), it's likely combos
    if unique_count > 20 and row_count > 10:
        # Check if some unique values are substrings of others (e.g., "A" appears in "A, B")
        unique_vals = [str(v) for v in series.dropna().unique()[:50]]
        substring_matches = 0
        for i, v1 in enumerate(unique_vals[:10]):
            for v2 in unique_vals[i+1:20]:
                if len(v1) < len(v2) and v1 in v2:
                    substring_matches += 1
        if substring_matches >= 3:
            return True
    
    # Strategy 3: Check if any comma-containing value exists and there are many unique values
    has_any_comma = any(',' in str(v) for v in sample if pd.notna(v))
    if has_any_comma and unique_count > 15:
        return True
    
    return False


def detect_grid_group(column_name: str) -> Optional[str]:
    """
    Detect if column is part of a grid question group.
    Grid questions often have patterns like:
    - "Rate [Product A]", "Rate [Product B]"
    - "Question 1 [Row A]", "Question 1 [Row B]"
    
    Returns the common prefix (group name) if detected.
    """
    # Look for bracketed suffixes
    bracket_match = re.match(r'^(.+?)\s*\[.+\]$', column_name)
    if bracket_match:
        return bracket_match.group(1).strip()
    
    # Look for parenthetical suffixes
    paren_match = re.match(r'^(.+?)\s*\(.+\)$', column_name)
    if paren_match:
        return paren_match.group(1).strip()
    
    return None


def detect_shared_response_columns(df: pd.DataFrame) -> dict:
    """
    Detect columns that share the exact same set of unique response values.
    This is a strong indicator of a Likert grid question (multiple statements, same scale).
    
    Returns a dict: {frozenset of column names: [list of unique values]}
    """
    # Get unique values for each column
    column_values = {}
    for col in df.columns:
        if df[col].dtype == 'object':
            # Get unique non-null values
            unique_vals = frozenset(
                str(v).strip() for v in df[col].dropna().unique() 
                if v is not None and str(v).strip()
            )
            if 2 <= len(unique_vals) <= 10:  # Typical Likert range
                column_values[col] = unique_vals
    
    # Group columns by their unique value sets
    value_to_columns = {}
    for col, vals in column_values.items():
        if vals in value_to_columns:
            value_to_columns[vals].append(col)
        else:
            value_to_columns[vals] = [col]
    
    # Filter to only groups with 2+ columns (actual grids)
    return {
        cols_tuple: list(vals)
        for vals, cols in value_to_columns.items()
        if len(cols) >= 2
        for cols_tuple in [tuple(cols)]
    }


def detect_numeric_likert(series: pd.Series) -> Tuple[bool, Optional[List[int]]]:
    """
    Detect if a numeric column is a Likert scale (1-5, 1-7, 1-10, 0-10).
    Returns (is_numeric_likert, ordered_values).
    """
    if not pd.api.types.is_numeric_dtype(series):
        return False, None
    
    clean = series.dropna()
    if clean.empty:
        return False, None
    
    unique_vals = sorted(clean.unique())
    
    # Common numeric Likert patterns
    # 1-5 scale
    if set(unique_vals).issubset({1, 2, 3, 4, 5}):
        return True, [1, 2, 3, 4, 5]
    # 1-7 scale
    if set(unique_vals).issubset({1, 2, 3, 4, 5, 6, 7}):
        return True, [1, 2, 3, 4, 5, 6, 7]
    # 0-10 NPS scale
    if set(unique_vals).issubset({0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10}):
        return True, list(range(0, 11))
    # 1-10 scale
    if set(unique_vals).issubset({1, 2, 3, 4, 5, 6, 7, 8, 9, 10}):
        return True, list(range(1, 11))
    
    return False, None


def detect_other_column(column_name: str, unique_count: int, row_count: int) -> bool:
    """
    Detect if a column is an "Other (please specify)" free-text field.
    These columns have:
    - Column name containing "other", "specify", "please describe"
    - High unique count (many different text responses)
    """
    name_lower = column_name.lower()
    
    # Check for "Other" patterns in column name
    other_patterns = ['other', 'specify', 'please describe', 'if other', 'else']
    has_other_pattern = any(p in name_lower for p in other_patterns)
    
    # High cardinality (many unique values relative to rows) suggests free-text
    high_cardinality = unique_count > 10 and unique_count / row_count > 0.3
    
    return has_other_pattern and high_cardinality

def infer_dtype(series: pd.Series) -> str:
    if is_datetime64_any_dtype(series):
        return 'temporal'
    
    # Try to convert to datetime to see if it works
    if series.dtype == 'object':
        try:
            pd.to_datetime(series.dropna().iloc[:100], errors='raise')
            # If successful, check if it's not mostly numbers (like year 2020, 2021 might be numeric or temporal)
            # For now, if it parses as date, lets assume temporal if the column name looks "date-ish" 
            # or if the values format is clearly date-like.
            # Simple heuristic:
            return 'temporal' # Requires verification after actual conversion attempt
        except:
            pass
            
    if is_numeric_dtype(series):
        # Check if it's actually an ID or categorical status (0, 1)
        # If unique count is low, it might be ordinal/nominal
        if series.nunique() < 12: # Slightly higher threshold
            # If values are floats, it's likely numeric (measurement)
            if pd.api.types.is_float_dtype(series):
                return 'numeric'
            
            # If integers, check magnitude
            # Small integers (1-10) are likely ordinal/categories
            # Large integers (>100) are likely quantities (Sales, Population)
            if series.max() > 50: 
                return 'numeric'
                
            return 'ordinal'
        return 'numeric'
        
    if series.nunique() < 50:
        return 'nominal'
        
    return 'nominal' # Default to text/nominal

@track_performance("profile_dataset")
def profile_dataset(df: pd.DataFrame) -> DatasetProfile:
    """
    Profile a dataset and return metadata about its structure and columns.
    Optimized to reduce DataFrame operations and memory usage.
    """
    # Pre-compute which columns are object type to avoid repeated checks
    # Use list comprehension for efficiency
    object_cols = [col for col, dtype in zip(df.columns, df.dtypes) if dtype == 'object']
    
    # Attempt to convert object columns to datetime where possible
    # Use vectorized operations where possible
    # Only process first 1000 rows for datetime detection to improve performance
    sample_size = min(1000, len(df))
    for col in object_cols:
        try:
            # Be conservative: only convert if highly likely
            # Sample first rows for faster detection
            sample = df[col].dropna().head(sample_size)
            if sample.empty:
                continue
            
            # First: Try stripping currency/symbols and converting to numeric
            # This handles "$100", "€50.00", "1,000", "50%"
            first_valid = str(sample.iloc[0]) if not sample.empty else ""
            if any(c in first_valid for c in ['$', '€', '£', '¥', '%', ',']):
                # Try to parse as numeric after stripping symbols
                clean_sample = sample.astype(str).str.replace(r'[$€£¥%,]', '', regex=True).str.strip()
                numeric_sample = pd.to_numeric(clean_sample, errors='coerce')
                if numeric_sample.notna().mean() > 0.8:  # 80% success
                    # Apply to entire column
                    df[col] = pd.to_numeric(
                        df[col].astype(str).str.replace(r'[$€£¥%,]', '', regex=True).str.strip(),
                        errors='coerce'
                    )
                    logger.debug(f"Converted currency column {col} to numeric")
                    continue  # Skip datetime check for this column
                
            first_valid = sample.iloc[0] if not sample.empty else None
            if first_valid and isinstance(first_valid, str) and len(first_valid) > 6:
                # Try parsing sample first
                temp_sample = pd.to_datetime(sample, errors='coerce')
                if temp_sample.notna().mean() > 0.8:  # If 80% parse successfully
                    # Only then convert entire column
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                    logger.debug(f"Converted column {col} to datetime")
        except Exception as e:
            logger.debug(f"Could not convert column {col}: {e}")

    columns = []
    
    # Process columns in a single pass to reduce DataFrame operations
    # Use iteritems for better performance with large DataFrames
    for col_name in df.columns:
        series = df[col_name]
        dtype = infer_dtype(series)
        
        # Calculate stats efficiently using vectorized operations
        # Use single pass for null count and unique count
        null_count = int(series.isna().sum())
        
        # Only dropna if needed (avoid unnecessary copy)
        if null_count > 0:
            clean_series = series.dropna()
        else:
            clean_series = series
        
        # Calculate unique count only once (cached by pandas)
        unique_count = int(series.nunique())
        
        min_val = None
        max_val = None
        mean_val = None
        
        if dtype == 'temporal':
            if not clean_series.empty:
                # Ensure we can get min/max for dates
                try:
                    min_val_dt = clean_series.min()
                    max_val_dt = clean_series.max()
                    # Convert to ISO format string for JSON serialization
                    if hasattr(min_val_dt, 'isoformat'):
                        min_val = min_val_dt.isoformat()
                    else:
                        min_val = str(min_val_dt)
                    
                    if hasattr(max_val_dt, 'isoformat'):
                        max_val = max_val_dt.isoformat()
                    else:
                        max_val = str(max_val_dt)
                except Exception as e:
                    logger.warning(f"Error processing temporal column {col_name}: {e}")
                    min_val = None
                    max_val = None
        
        elif is_numeric_dtype(series):
            if not clean_series.empty:
                # Calculate all numeric stats in one pass
                min_val = float(clean_series.min())
                max_val = float(clean_series.max())
                mean_val = float(clean_series.mean())
        
        # Get examples - use head() which is efficient
        examples = clean_series.head(3).tolist()
        
        # Survey data detection
        is_checkbox = False
        is_likert = False
        likert_order = None
        grid_group = None
        is_other_column = False
        is_numeric_likert_scale = False
        
        # Check for numeric Likert scales (1-5, 1-10, etc.)
        if is_numeric_dtype(series) and dtype == 'ordinal':
            is_numeric_likert_scale, numeric_likert_order = detect_numeric_likert(series)
            if is_numeric_likert_scale:
                is_likert = True
                likert_order = [str(v) for v in numeric_likert_order]  # Convert to strings for consistency
        
        # Only check for survey patterns in nominal/ordinal columns
        if dtype in ('nominal', 'ordinal') and not is_numeric_dtype(series):
            # Check for checkbox (multi-select) data
            is_checkbox = detect_checkbox_column(series)
            
            # Check for Likert scale
            if not is_checkbox:
                unique_vals = [str(v) for v in clean_series.unique()[:20] if v is not None and pd.notna(v)]
                is_likert, likert_order = detect_likert_scale(unique_vals)
                if is_likert:
                    dtype = 'ordinal'  # Upgrade to ordinal if Likert detected
            
            # Check for grid question pattern
            grid_group = detect_grid_group(col_name)
            
            # Check for "Other (please specify)" columns
            is_other_column = detect_other_column(col_name, unique_count, len(df))
        
        columns.append(ColumnProfile(
            name=col_name,
            original_name=col_name,
            dtype=dtype,
            null_count=null_count,
            unique_count=unique_count,
            examples=examples,
            min=min_val,
            max=max_val,
            mean=mean_val,
            is_checkbox=is_checkbox,
            is_likert=is_likert,
            likert_order=likert_order,
            grid_group=grid_group
        ))
    
    return DatasetProfile(
        row_count=len(df),
        col_count=len(df.columns),
        columns=columns
    )
