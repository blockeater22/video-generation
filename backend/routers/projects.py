from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from db import db
from core import now_iso, gen_id
from deps import get_current_org, get_current_user, clean
from schemas import ProjectCreate

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("")
async def list_projects(org: dict = Depends(get_current_org)):
    return await db.projects.find({"organization_id": org["id"]}, {"_id": 0}).sort("created_at", -1).to_list(500)


@router.post("")
async def create_project(body: ProjectCreate, org: dict = Depends(get_current_org), user: dict = Depends(get_current_user)):
    doc = {"id": gen_id("prj"), "organization_id": org["id"], "name": body.name,
           "description": body.description, "created_by": user["id"],
           "created_at": now_iso(), "updated_at": now_iso()}
    await db.projects.insert_one(doc)
    return clean(doc)


@router.delete("/{pid}", status_code=204)
async def delete_project(pid: str, org: dict = Depends(get_current_org)):
    await db.projects.delete_one({"id": pid, "organization_id": org["id"]})
    return JSONResponse(status_code=204, content=None)
