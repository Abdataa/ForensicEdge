from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from models.feedback import Feedback

router = APIRouter(prefix="/feedback", tags=["Feedback"])

@router.post("/")
def submit_feedback(evidence_id: int, comment: str, is_correct: bool, db: Session = Depends(get_db)):
    new_feedback = Feedback(evidence_id=evidence_id, comment=comment, is_correct=is_correct)
    db.add(new_feedback)
    db.commit()
    return {"message": "Feedback recorded for model improvement"}