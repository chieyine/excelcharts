import logging
import hashlib
import pandas as pd
from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.services.parser import parse_file, clean_dataframe, validate_file_content
from app.services.profiler import profile_dataset
from app.services.inference import infer_charts
from app.services.generator import generate_vega_spec
from app.services.insights import generate_insights
from app.services.surprise import generate_surprise
from app.core.schemas import AnalysisResult, ChartCandidate
from app.core.errors import ErrorCodes, get_error_response
from app.core.config import get_settings
from app.core.sanitization import sanitize_filename, sanitize_for_logging
from app.core.performance import track_performance, PerformanceMonitor
from app.core.cache import get_file_cache, get_profile_cache, generate_file_cache_key, generate_profile_cache_key
from app.services.ai_insights import (
    generate_ai_insights, 
    suggest_data_cleaning, 
    generate_executive_summary
)

logger = logging.getLogger(__name__)

# Get centralized configuration
settings = get_settings()

router = APIRouter()

def get_limiter(request: Request) -> Limiter:
    """Get rate limiter from app state using dependency injection."""
    return request.app.state.limiter

@router.get("/health")
async def health_check():
    return {"status": "ok"}

async def _check_file_size_streaming(file: UploadFile) -> int:
    """
    Check file size using streaming to avoid loading entire file into memory.
    Returns the file size in bytes.
    """
    file_size = 0
    chunk_size = 1024 * 1024  # 1MB chunks
    
    # Reset file pointer
    await file.seek(0)
    
    # Read in chunks to check size
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        file_size += len(chunk)
        
        # Early exit if file exceeds limit
        if file_size > settings.max_file_size_bytes:
            break
    
    # Reset file pointer for actual parsing
    await file.seek(0)
    return file_size

async def _process_upload(file: UploadFile, request: Request, skip_ai: bool = False) -> AnalysisResult:
    """Process file upload (internal function without rate limiting)."""
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    
    try:
        # Validate file size using streaming to avoid memory issues
        file_size = await _check_file_size_streaming(file)
        
        if file_size > settings.max_file_size_bytes:
            error_info = get_error_response(
                ErrorCodes.FILE_TOO_LARGE,
                f"Maximum size is {settings.max_file_size_mb}MB. Your file is {file_size / 1024 / 1024:.2f}MB"
            )
            error_info['correlation_id'] = correlation_id
            raise HTTPException(
                status_code=413,
                detail=error_info
            )
        
        if file_size == 0:
            error_info = get_error_response(ErrorCodes.FILE_EMPTY)
            error_info['correlation_id'] = correlation_id
            raise HTTPException(status_code=400, detail=error_info)
        
        # Sanitize filename for logging (prevent log injection)
        safe_filename = sanitize_filename(file.filename) if file.filename else 'unknown'
        logger.info(
            f"Processing file: {sanitize_for_logging(safe_filename)}, size: {file_size / 1024:.2f}KB"
        )
        
        # 1. Parse (with caching)
        # Read file content for cache key
        await file.seek(0)
        file_content = await file.read()
        await file.seek(0)
        
        cache_key = generate_file_cache_key(file_content, safe_filename)
        file_cache = get_file_cache()
        
        # Try cache first
        cached_df = file_cache.get(cache_key)
        if cached_df is not None:
            logger.info(
                f"Using cached parsed file: {sanitize_for_logging(safe_filename)}"
            )
            df = cached_df.copy()  # Copy to avoid modifying cached data
        else:
            df = await parse_file(file)
            # Cache the parsed dataframe
            file_cache.set(cache_key, df.copy(), ttl=1800)  # 30 minutes
        
        # Validate file content after parsing
        validate_file_content(df, safe_filename)
        
        df = clean_dataframe(df)
        
        if df.empty:
            error_info = get_error_response(ErrorCodes.PARSE_ERROR, "File appears to be empty or contains no valid data after cleaning")
            error_info['correlation_id'] = correlation_id
            raise HTTPException(
                status_code=400,
                detail=error_info
            )
        
        # 2. Profile (with caching)
        profile_cache = get_profile_cache()
        
        # Generate cache key based on dataframe characteristics
        # Use row count, col count, and column names/dtypes as key
        cache_key_data = f"{len(df)}:{len(df.columns)}:{','.join(f'{c}:{str(df[c].dtype)}' for c in df.columns)}"
        profile_cache_key = hashlib.sha256(cache_key_data.encode()).hexdigest()
        
        # Try cache first
        cached_profile = profile_cache.get(profile_cache_key)
        if cached_profile is not None:
            logger.info(
                f"Using cached profile for dataset: {cached_profile.row_count} rows, {cached_profile.col_count} columns"
            )
            profile = cached_profile
        else:
            # Profile the dataset
            profile = profile_dataset(df)
            # Cache the profile
            profile_cache.set(profile_cache_key, profile, ttl=3600)  # 1 hour
        
        logger.info(
            f"Profiled dataset: {profile.row_count} rows, {profile.col_count} columns"
        )
        
        # 3. Infer charts
        # Prepare sample data for AI inference
        sample_rows = df.head(10).replace({float('nan'): None}).to_dict(orient='records')
        candidates = infer_charts(profile, sample_rows)
        
        # Handle empty candidates with fallback
        if not candidates:
            logger.warning("No chart candidates generated, creating fallback table view")
            # Create a fallback table view
            if len(df.columns) > 0:
                fallback_spec = generate_vega_spec(
                    chart_type="bar",  # Use bar as fallback (table not directly supported in Vega-Lite)
                    x=df.columns[0],
                    title="Data Overview",
                    x_type="nominal"
                )
                candidates = [ChartCandidate(
                    chart_type="table",
                    x_column=df.columns[0],
                    title="Data Table",
                    description="Displaying data in table format",
                    score=0.5,
                    spec=fallback_spec
                )]
            else:
                error_info = get_error_response(ErrorCodes.PROCESSING_ERROR, "Unable to generate charts from this data")
                error_info['correlation_id'] = correlation_id
                raise HTTPException(
                    status_code=400,
                    detail=error_info
                )
        
        # 4. Prepare Response
        # Limit data size for performant JSON response
        # Use iloc for efficient slicing instead of copy + head
        if len(df) > settings.max_dataset_rows:
            response_df = df.iloc[:settings.max_dataset_rows].copy()
            logger.info(
                f"Dataset truncated from {len(df)} to {settings.max_dataset_rows} rows for response"
            )
        else:
            response_df = df
        
        # Convert timestamps to ISO format strings for JSON serialization
        # Only process datetime columns (more efficient than checking all columns)
        datetime_cols = [col for col in response_df.columns 
                        if pd.api.types.is_datetime64_any_dtype(response_df[col])]
        for col in datetime_cols:
            response_df[col] = response_df[col].dt.strftime('%Y-%m-%dT%H:%M:%S')
        
        # Use records orientation which is most efficient for JSON serialization
        dataset = response_df.to_dict(orient='records')
        
        # 5. Generate enhanced insights
        insights = generate_insights(profile, response_df)
        
        # 6. Generate surprise discovery (optional)
        surprise = None
        try:
            surprise = generate_surprise(profile, response_df)
        except Exception as e:
            logger.debug(f"Surprise generation failed: {e}")
        
        # 7. Generate AI-powered insights (optional, depends on GROQ_API_KEY and skip_ai flag)
        if not skip_ai:
            try:
                data_summary = {
                    "row_count": profile.row_count,
                    "column_count": len(profile.columns)
                }
                column_profiles = [
                    {"name": col.name, "dtype": col.dtype, "unique_count": col.unique_count, "null_count": getattr(col, 'null_count', 0)}
                    for col in profile.columns
                ]
                logger.info(f"Calling AI insights with {len(column_profiles)} columns")
            
                # Pass the specific columns being charted for better insights
                recommended = candidates[0]
                ai_insight = generate_ai_insights(
                    data_summary, 
                    recommended.chart_type, 
                    column_profiles,
                    x_column=recommended.x_column,
                    y_column=recommended.y_column
                )
                if ai_insight:
                    # Prepend AI insight to regular insights
                    insights = ["🤖 " + ai_insight] + insights
                    logger.info("AI insight added to response")
                else:
                    logger.info("AI insight returned None - no AI providers configured?")
            
                # 8. Add data cleaning suggestions (works with or without AI)
                cleaning_suggestions = suggest_data_cleaning(column_profiles, profile.row_count)
                insights = insights + cleaning_suggestions
            
            except Exception as e:
                logger.warning(f"AI insight generation failed: {e}")
        else:
            logger.info("AI insights skipped (skip_ai=True)")
        
        logger.info(
            f"Successfully processed file: {sanitize_for_logging(safe_filename)}, generated {len(candidates)} chart candidates, {len(insights)} insights"
        )
        
        return AnalysisResult(
            filename=safe_filename or "uploaded_file",
            profile=profile,
            recommended_chart=candidates[0],
            alternatives=candidates[1:],
            dataset=dataset,
            insights=insights,
            surprise=surprise
        )
    except HTTPException:
        raise

# Register the rate-limited endpoint
# Rate limiting is handled via slowapi middleware configured in main.py
@router.post("/upload", response_model=AnalysisResult)
async def upload_file(
    request: Request, 
    file: UploadFile = File(...),
    skip_ai: bool = False
):
    """
    Upload and analyze a file to generate chart recommendations.
    
    Args:
        file: CSV or Excel file to analyze
        skip_ai: If True, skip AI insights generation (faster, no token cost)
    
    Rate limited to 10 requests per minute per IP address (configurable).
    """
    # Get limiter and settings from app state
    limiter = request.app.state.limiter
    app_settings = request.app.state.settings
    
    # Apply rate limit using slowapi's decorator pattern
    limit_decorator = limiter.limit(f"{app_settings.rate_limit_per_minute}/minute")
    
    @limit_decorator
    async def _rate_limited_handler(request: Request):
        return await _process_upload(file, request, skip_ai=skip_ai)
    
    try:
        # Call the rate-limited handler
        # This will raise RateLimitExceeded if limit exceeded (handled by main.py)
        return await _rate_limited_handler(request)
    except HTTPException:
        raise
    except RateLimitExceeded:
        # Re-raise to let exception handler in main.py format the response
        raise
    except Exception as e:
        correlation_id = getattr(request.state, 'correlation_id', 'unknown')
        safe_filename = sanitize_for_logging(sanitize_filename(file.filename) if file.filename else 'unknown')
        logger.error(
            f"Unexpected error processing file {safe_filename}: {e}",
            exc_info=True
        )
        error_info = get_error_response(ErrorCodes.UNKNOWN_ERROR)
        error_info['correlation_id'] = correlation_id
        raise HTTPException(status_code=500, detail=error_info)


@router.post("/insights/summary")
async def get_executive_summary_endpoint(
    request: Request,
    file: UploadFile = File(...)
):
    """Generate an executive summary for the uploaded file."""
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    
    try:
        # Reuse file processing caching logic manually to retrieve parsed data
        # 1. Check size (quick check)
        file_content = await file.read()
        await file.seek(0)
        
        safe_filename = sanitize_filename(file.filename) if file.filename else 'unknown'
        cache_key = generate_file_cache_key(file_content, safe_filename)
        file_cache = get_file_cache()
        
        # Try cache first
        df = file_cache.get(cache_key)
        if df is None:
            # Re-parse if not in cache (fallback)
            df = await parse_file(file)
            validate_file_content(df, safe_filename)
            df = clean_dataframe(df)
            file_cache.set(cache_key, df.copy(), ttl=1800)
            
        if df.empty:
            raise HTTPException(status_code=400, detail="File is empty")
            
        # 3. Profile
        profile_cache = get_profile_cache()
        cache_key_data = f"{len(df)}:{len(df.columns)}:{','.join(f'{c}:{str(df[c].dtype)}' for c in df.columns)}"
        profile_cache_key = hashlib.sha256(cache_key_data.encode()).hexdigest()
        
        profile = profile_cache.get(profile_cache_key)
        if profile is None:
            profile = profile_dataset(df)
            profile_cache.set(profile_cache_key, profile, ttl=3600)
            
        # 4. Generate Summary
        # Prepare sample data (first 5 rows)
        sample_data = df.head(5).to_dict(orient='records')
        
        summary = generate_executive_summary(profile.dict(), sample_data)
        
        if not summary:
             return {"summary": "## Summary Unavailable\n\nAI service is currently unavailable or could not generate a summary."}
             
        return {"summary": summary}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Executive summary generation failed: {e}")
        error_info = get_error_response(ErrorCodes.INTERNAL_ERROR, str(e))
        error_info['correlation_id'] = correlation_id
        raise HTTPException(status_code=500, detail=error_info)
