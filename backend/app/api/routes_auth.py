# backend/app/api/routes_auth.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from core.database import get_db
from core.security import verify_password, create_access_token
from models.user import User
from models.audit_log import AuditLog
import uuid
from datetime import datetime

router = APIRouter()

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict

@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    LOGIN ENDPOINT - Same for ALL Users
    Returns JWT token with user role for frontend redirection
    """
    
    # 1. Find user by email
    user = db.query(User).filter(User.email == request.email).first()
    
    # 2. Check if user exists
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # 3. Check if account is active
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")
    
    # 4. Verify password
    if not verify_password(request.password, user.password_hash):
        # Log failed attempt
        _log_audit(db, user.user_id, user.email, "login_failed", "Invalid password")
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # 5. Update last login time
    user.last_login = datetime.utcnow()
    db.commit()
    
    # 6. Create JWT token with ROLE
    token_data = {
        "sub": str(user.user_id),
        "email": user.email,
        "role": user.role,  # ← CRITICAL: Role embedded in token!
        "name": user.full_name
    }
    access_token = create_access_token(token_data)
    
    # 7. Log successful login
    _log_audit(db, user.user_id, user.email, "login_success", f"Role: {user.role}")
    
    # 8. Return token and user info
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.user_id),
            "name": user.full_name,
            "email": user.email,
            "role": user.role,  # ← Frontend uses this to redirect!
            "badge_number": user.badge_number,
            "department": user.department
        }
    }

def _log_audit(db, user_id, email, action, details):
    """Helper to log audit events"""
    log = AuditLog(
        log_id=uuid.uuid4(),
        user_id=user_id,
        user_email=email,
        action=action,
        details={"message": details},
        timestamp=datetime.utcnow()
    )
    db.add(log)
    db.commit()