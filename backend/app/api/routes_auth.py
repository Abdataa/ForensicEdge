# backend/app/api/routes_auth.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import datetime

from core.database import get_db
from services.auth_service import login_user
from models.user import User
from models.audit_log import AuditLog
import uuid

router = APIRouter()

# Request schema
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# Response schema
class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    User login endpoint.
    Returns JWT token and user info.
    """
    # Call login service
    result = login_user(db, request.email, request.password)
    
    if not result:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Update last login time
    user = db.query(User).filter(User.email == request.email).first()
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Log successful login (optional)
    audit_log = AuditLog(
        log_id=uuid.uuid4(),
        user_id=user.user_id,
        user_email=user.email,
        action="login_success",
        timestamp=datetime.utcnow()
    )
    db.add(audit_log)
    db.commit()
    
    return result