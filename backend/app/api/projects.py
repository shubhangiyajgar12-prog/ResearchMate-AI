from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)

from sqlalchemy.orm import Session

from app.database.database import get_db

from app.models.research_project import ResearchProject

from app.schemas.research_project import (
    ResearchProjectCreate,
    ResearchProjectUpdate,
    ResearchProjectResponse
)


router = APIRouter(
    prefix="/projects",
    tags=["Research Projects"]
)


# ==================================================
# CREATE PROJECT
# ==================================================

@router.post(
    "/",
    response_model=ResearchProjectResponse
)
def create_project(
    project: ResearchProjectCreate,
    db: Session = Depends(get_db)
):

    new_project = ResearchProject(

        title=project.title,

        description=project.description,

        research_field=project.research_field

    )

    db.add(new_project)

    db.commit()

    db.refresh(new_project)

    return new_project


# ==================================================
# GET ALL PROJECTS
# ==================================================

@router.get(
    "/",
    response_model=list[ResearchProjectResponse]
)
def get_projects(
    db: Session = Depends(get_db)
):

    projects = (

        db.query(ResearchProject)

        .order_by(
            ResearchProject.id.desc()
        )

        .all()

    )

    return projects


# ==================================================
# GET SINGLE PROJECT
# ==================================================

@router.get(
    "/{project_id}",
    response_model=ResearchProjectResponse
)
def get_project(
    project_id: int,
    db: Session = Depends(get_db)
):

    project = (

        db.query(ResearchProject)

        .filter(
            ResearchProject.id == project_id
        )

        .first()

    )


    if project is None:

        raise HTTPException(
            status_code=404,
            detail="Research project not found"
        )


    return project


# ==================================================
# UPDATE PROJECT
# ==================================================

@router.put(
    "/{project_id}",
    response_model=ResearchProjectResponse
)
def update_project(
    project_id: int,
    project_data: ResearchProjectUpdate,
    db: Session = Depends(get_db)
):

    project = (

        db.query(ResearchProject)

        .filter(
            ResearchProject.id == project_id
        )

        .first()

    )


    if project is None:

        raise HTTPException(
            status_code=404,
            detail="Research project not found"
        )


    project.title = project_data.title

    project.description = project_data.description

    project.research_field = project_data.research_field

    project.status = project_data.status


    db.commit()

    db.refresh(project)

    return project


# ==================================================
# DELETE PROJECT
# ==================================================

@router.delete(
    "/{project_id}"
)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db)
):

    project = (

        db.query(ResearchProject)

        .filter(
            ResearchProject.id == project_id
        )

        .first()

    )


    if project is None:

        raise HTTPException(
            status_code=404,
            detail="Research project not found"
        )


    db.delete(project)

    db.commit()


    return {

        "message":
        "Research project deleted successfully",

        "project_id":
        project_id

    }