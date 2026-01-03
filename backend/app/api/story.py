"""
Story Mode API endpoint - Generate PDF reports.
"""
import logging
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
from app.services.story import generate_story
from app.services.pdf_generator import create_pdf
from app.core.schemas import AnalysisResult
import io

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/story")
async def generate_story_pdf(result: AnalysisResult, format: str = "pdf"):
    """
    Generate a one-page PDF report from analysis result.
    
    Args:
        result: Analysis result with charts and insights
        format: Output format - "pdf" or "json" (default: "pdf")
    """
    try:
        story = generate_story(
            profile=result.profile,
            recommended_chart=result.recommended_chart,
            alternatives=result.alternatives,
            insights=result.insights or [],
            filename=result.filename
        )
        
        if format == "json":
            return {
                "story": story,
                "message": "Story structure generated. Use format=pdf to get PDF file."
            }
        
        # Generate PDF
        # Note: Chart images would need to be generated from Vega-Lite specs
        # For now, PDF includes text and structure
        pdf_bytes = create_pdf(story, chart_images=None)
        
        # Return PDF as download
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{result.filename}_report.pdf"'
            }
        )
    except Exception as e:
        logger.error(f"Error generating story: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate story: {str(e)}"
        )

