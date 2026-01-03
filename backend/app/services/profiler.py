import logging
import pandas as pd
import numpy as np
from app.core.schemas import ColumnProfile, DatasetProfile
from app.core.performance import track_performance
from pandas.api.types import is_numeric_dtype, is_datetime64_any_dtype

logger = logging.getLogger(__name__)

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
        
        columns.append(ColumnProfile(
            name=col_name,
            original_name=col_name,
            dtype=dtype,
            null_count=null_count,
            unique_count=unique_count,
            examples=examples,
            min=min_val,
            max=max_val,
            mean=mean_val
        ))
    
    return DatasetProfile(
        row_count=len(df),
        col_count=len(df.columns),
        columns=columns
    )
