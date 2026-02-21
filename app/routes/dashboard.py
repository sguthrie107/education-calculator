"""Dashboard routes."""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path
import json

from ..database import get_db
from ..models import Child
from ..services.comparison import get_all_children_comparison

router = APIRouter()

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    """Main dashboard view — loads all children and their projections."""
    children = db.query(Child).all()
    child_names = [c.name for c in children]

    initial_data = None
    if child_names:
        try:
            initial_data = get_all_children_comparison(db)
        except Exception as e:
            print(f"Error fetching initial data: {e}")
            import traceback
            traceback.print_exc()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "children": child_names,
            "initial_data": initial_data,
        },
    )
