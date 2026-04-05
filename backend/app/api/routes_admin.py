from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from models.user import User

router = APIRouter(prefix="/api/admin", tags=["Admin Management"])

@router.get("/users")
def list_all_users(db: Session = Depends(get_db)):
    return db.query(User).all()

@router.delete("/users/{user_id}")
def deactivate_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"message": f"User {user_id} removed from system"}