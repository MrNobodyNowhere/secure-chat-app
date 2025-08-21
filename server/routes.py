from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .schemas import UserOut


router = APIRouter()


@router.get("/users", response_model=List[UserOut])
def list_users(db: Session = Depends(get_db)):
	return db.query(User).order_by(User.username.asc()).all()

