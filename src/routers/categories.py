from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_

from src.database import get_db
from src.models import Category, Transaction, User
from src.schemas.categories import CategoryCreate, CategoryOut
from src.auth import get_current_user

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # Return global categories (user_id IS NULL) + user's own categories
    return db.query(Category).filter(
        or_(Category.user_id == None, Category.user_id == user.id)
    ).order_by(Category.name).all()


@router.post("", response_model=CategoryOut)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cat = Category(**payload.model_dump(), user_id=user.id)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.delete("/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(404, "Category not found")
    # Only allow deleting own categories, not global ones
    if cat.user_id is not None and cat.user_id != user.id:
        raise HTTPException(403, "Not your category")
    if cat.user_id is None:
        raise HTTPException(400, "Cannot delete default categories")
    tx_count = db.query(Transaction).filter(Transaction.category_id == category_id).count()
    if tx_count > 0:
        raise HTTPException(400, "Cannot delete category with existing transactions")
    db.delete(cat)
    db.commit()
    return {"ok": True}
