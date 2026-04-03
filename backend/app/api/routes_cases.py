from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from models.case import Case 

router = APIRouter(prefix="/cases", tags=["Case Management"])

@router.post("/")
def create_case(title: str, case_num: str, investigator: str, db: Session = Depends(get_db)):
    new_case = Case(title=title, case_number=case_num, investigator_name=investigator)
    db.add(new_case)
    db.commit()
    db.refresh(new_case)
    return {"status": "success", "data": new_case}

@router.get("/{case_id}")
def get_case(case_id: int, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case