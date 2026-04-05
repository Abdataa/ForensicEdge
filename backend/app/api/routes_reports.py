from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from sqlalchemy.orm import Session # <--- Add this
from core.database import get_db    # <--- Add this
from models.case import Case
import os
router = APIRouter(prefix="/api/reports", tags=["Reports"])

# ... (inside your router file)

@router.get("/{case_id}/report")
def generate_case_report(case_id: int, db: Session = Depends(get_db)):
    # 1. Fetch data from DB
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # 2. Create PDF file path
    report_path = f"storage/reports/Case_{case_id}_Report.pdf"
    os.makedirs("storage/reports", exist_ok=True)
    
    # 3. Build the PDF
    c = canvas.Canvas(report_path, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, f"ForensicEdge Investigation Report")
    c.setFont("Helvetica", 12)
    c.drawString(100, 730, f"Case Title: {case.title}")
    c.drawString(100, 715, f"Investigator: {case.investigator_name}")
    c.drawString(100, 700, "--------------------------------------------------")
    
    # Add Evidence List
    c.drawString(100, 680, "Evidence Summary:")
    y_position = 660
    for item in case.evidence:
        c.drawString(120, y_position, f"- {item.filename} (Hash: {item.sha256_hash[:15]}...)")
        y_position -= 20
        
    c.save()
    
    return FileResponse(report_path, media_type='application/pdf', filename=f"Report_Case_{case_id}.pdf")