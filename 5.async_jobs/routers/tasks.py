from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid
from database import models, database
from routers import models as schemas
import auth

router = APIRouter(prefix="/tasks", tags=["Tasks"])

@router.post("/", response_model=schemas.TaskOut)
def submit_task(payload: schemas.TaskCreate, db: Session = Depends(database.get_db), user = Depends(auth.get_current_user)):
    task_id = str(uuid.uuid4())
    task = models.Task(id=task_id, user=user["username"], params=payload.params, status="pending")
    db.add(task)
    db.commit()
    db.refresh(task)
    return task

@router.get("/{task_id}", response_model=schemas.TaskOut)
def get_task(task_id: str, db: Session = Depends(database.get_db), user = Depends(auth.get_current_user)):
    task = db.query(models.Task).filter(models.Task.id == task_id, models.Task.user == user["username"]).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在或无权限")
    return task
