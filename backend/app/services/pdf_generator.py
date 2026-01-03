"""
PDF generation for Story Mode reports.
"""
import logging
import io
from typing import List, Dict, Any
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.colors import HexColor
from PIL import Image as PILImage

logger = logging.getLogger(__name__)

# Color scheme
PRIMARY_COLOR = HexColor('#1a1a1a')
SECONDARY_COLOR = HexColor('#666666')
ACCENT_COLOR = HexColor('#3b82f6')
BACKGROUND_COLOR = HexColor('#f8f9fa')


def create_pdf(story_data: Dict[str, Any], chart_images: List[bytes] = None) -> bytes:
    """
    Generate a PDF report from story data.
    
    Args:
        story_data: Story structure from generate_story()
        chart_images: Optional list of chart image bytes (PNG)
        
    Returns:
        PDF file as bytes
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.75*inch, bottomMargin=0.75*inch)
    
    # Container for the 'Flowable' objects
    story_content = []
    
    # Define styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=PRIMARY_COLOR,
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=18,
        textColor=PRIMARY_COLOR,
        spaceAfter=8,
        spaceBefore=16,
        fontName='Helvetica-Bold'
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=11,
        textColor=SECONDARY_COLOR,
        spaceAfter=12,
        alignment=TA_JUSTIFY,
        leading=14
    )
    
    insight_style = ParagraphStyle(
        'InsightStyle',
        parent=styles['BodyText'],
        fontSize=11,
        textColor=PRIMARY_COLOR,
        spaceAfter=8,
        leftIndent=20,
        bulletIndent=10,
        bulletFontName='Helvetica-Bold'
    )
    
    # Title
    story_content.append(Paragraph(story_data['title'], title_style))
    story_content.append(Spacer(1, 0.3*inch))
    
    # Executive Summary
    story_content.append(Paragraph("Executive Summary", heading_style))
    story_content.append(Paragraph(story_data['summary'], body_style))
    story_content.append(Spacer(1, 0.2*inch))
    
    # Key Insights
    if story_data.get('insights'):
        story_content.append(Paragraph("Key Insights", heading_style))
        for insight in story_data['insights']:
            # Remove emoji for cleaner PDF
            clean_insight = insight
            for emoji in ['📈', '📉', '➡️', '⚠️', '🏆', '💎', '🎯', '🚀', '🔗', '📊', 'ℹ️', '🎲']:
                clean_insight = clean_insight.replace(emoji, '')
            story_content.append(Paragraph(f"• {clean_insight.strip()}", insight_style))
        story_content.append(Spacer(1, 0.2*inch))
    
    # Charts Section
    if story_data.get('charts'):
        story_content.append(Paragraph("Visualizations", heading_style))
        
        for idx, chart in enumerate(story_data['charts']):
            story_content.append(Paragraph(f"<b>{chart['title']}</b>", body_style))
            story_content.append(Paragraph(chart.get('description', ''), body_style))
            
            # Add chart image if available
            if chart_images and idx < len(chart_images):
                try:
                    img = PILImage.open(io.BytesIO(chart_images[idx]))
                    img_width, img_height = img.size
                    # Scale to fit page width (with margins)
                    max_width = 7 * inch
                    if img_width > max_width:
                        scale = max_width / img_width
                        img_width = max_width
                        img_height = img_height * scale
                    
                    img_buffer = io.BytesIO()
                    img.save(img_buffer, format='PNG')
                    img_buffer.seek(0)
                    
                    chart_img = Image(img_buffer, width=img_width, height=img_height)
                    story_content.append(chart_img)
                except Exception as e:
                    logger.warning(f"Could not add chart image: {e}")
            
            story_content.append(Spacer(1, 0.15*inch))
    
    # Conclusion
    story_content.append(Paragraph("Conclusion", heading_style))
    story_content.append(Paragraph(story_data['conclusion'], body_style))
    story_content.append(Spacer(1, 0.2*inch))
    
    # Metadata footer
    metadata = story_data.get('metadata', {})
    footer_text = f"Generated from {metadata.get('filename', 'data file')} • {metadata.get('row_count', 0):,} rows analyzed"
    footer_style = ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontSize=9,
        textColor=HexColor('#999999'),
        alignment=TA_CENTER
    )
    story_content.append(Spacer(1, 0.3*inch))
    story_content.append(Paragraph(footer_text, footer_style))
    
    # Build PDF
    doc.build(story_content)
    
    # Get PDF bytes
    buffer.seek(0)
    pdf_bytes = buffer.read()
    buffer.close()
    
    return pdf_bytes

