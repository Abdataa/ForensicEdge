import hashlib
import os
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from models.case_evidence import CaseEvidence

router = APIRouter(prefix="/evidence", tags=["Evidence Management"])

UPLOAD_DIR = "storage/evidence_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload/{case_id}")
async def upload_evidence(case_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    # Forensic Integrity: Generate SHA-256
    file_hash = hashlib.sha256(contents).hexdigest()
    
    file_path = os.path.join(UPLOAD_DIR, f"{case_id}_{file.filename}")
    with open(file_path, "wb") as f:
        f.write(contents)
        
    new_evidence = CaseEvidence(
        case_id=case_id,
        filename=file.filename,
        file_path=file_path,
        sha256_hash=file_hash
    )
    db.add(new_evidence)
    db.commit()
    return {"message": "Evidence catalogued", "sha256": file_hash}

@router.post("/{evidence_id}/re-analyze")
def re_analyze_evidence(evidence_id: int, db: Session = Depends(get_db)):
    # Task: Re-run analysis without re-uploading
    evidence = db.query(CaseEvidence).filter(CaseEvidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    
    # Logic to trigger AI engine would go here
    return {"status": "Analysis triggered", "target": evidence.filename}