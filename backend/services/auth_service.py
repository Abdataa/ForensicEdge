# backend/app/services/auth_service.py
from sqlalchemy.orm import Session
from models.user import User
from core.security import verify_password, create_access_token

def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """
    Authenticate user by email and password.
    Returns User object if valid, None otherwise.
    """
    # Fetch user from database
    user = db.query(User).filter(User.email == email).first()
    
    # User not found
    if not user:
        return None
    
    # Verify password
    if not verify_password(password, user.password_hash):
        return None
    
    # User not active
    if not user.is_active:
        return None
    
    return user

def login_user(db: Session, email: str, password: str) -> dict | None:
    """
    Login user and return JWT token.
    Returns token dict if valid, None otherwise.
    """
    # Authenticate user
    user = authenticate_user(db, email, password)
    
    if not user:
        return None
    
    # Create JWT token
    token_data = {
        "sub": str(user.user_id),
        "email": user.email,
        "role": user.role,
        "name": user.full_name
    }
    
    access_token = create_access_token(token_data)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.user_id),
            "name": user.full_name,
            "email": user.email,
            "role": user.role
        }
    }