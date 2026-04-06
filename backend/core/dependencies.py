from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from core.database import get_db
from core.security import decode_token
from models.user import User
import uuid

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = payload.get("sub")
    user = db.query(User).filter(User.user_id == uuid.UUID(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def require_role(roles: list):
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail=f"Requires role: {roles}")
        return current_user
    return role_checker

require_admin = require_role(["admin"])
require_analyst = require_role(["analyst", "admin"])
require_ai_engineer = require_role(["ai_engineer", "admin"])