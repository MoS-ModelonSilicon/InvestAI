from fastapi import APIRouter

from src.services.education import get_all_content, get_categories

router = APIRouter(prefix="/api/education", tags=["education"])


@router.get("")
def education_content():
    return {"categories": get_categories(), "articles": get_all_content()}
