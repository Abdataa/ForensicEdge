from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from core.database import get_db
from models.user import User
# You'll likely need a security utility file for these:
# from core.security import create_access_token, get_password_hash, verify_password

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register")
def register_user(username: str, email: str, password: str, db: Session = Depends(get_db)):
    # Check if user exists
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # In a real app, use: hashed_password = get_password_hash(password)
    new_user = User(full_name=username, email=email, password_hash=password) 
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created successfully", "user_id": new_user.id}

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or user.hashed_password != form_data.password: # Simplify for now
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # This is where you'd return a JWT token
    return {"access_token": "mock_token_for_now", "token_type": "bearer"}