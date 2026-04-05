from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from models.similarity_result import SimilarityResult

router = APIRouter(prefix="/api/compare", tags=["AI Comparison"])

@router.get("/results/{evidence_id}")
def get_comparison_results(evidence_id: int, db: Session = Depends(get_db)):
    # Pulls the AI's top matches for a specific piece of evidence
    results = db.query(SimilarityResult).filter(
        SimilarityResult.source_evidence_id == evidence_id
    ).all()
    
    if not results:
        return {"message": "No matches found yet. Analysis may be in progress."}
    return results

@router.post("/run-match")
def manual_match_trigger(evidence_id_1: int, evidence_id_2: int):
    # Allows a researcher to manually compare two specific items
    return {"status": "Comparison task queued", "pair": [evidence_id_1, evidence_id_2]}