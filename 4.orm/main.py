import uvicorn
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from models import Base, Task, User
from database import engine, SessionLocal

Base.metadata.create_all(bind=engine)

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

current_user = {
    "id": 1
}

@app.get("/tasks/me")
def list_my_tasks(db: Session = Depends(get_db)):
    return db.query(Task).filter(Task.user_id == current_user["id"]).all()


@app.get("/tasks/{task_id}")
def get_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task or task.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    return task

if __name__ == "__main__":
    uvicorn.run(app, port=8000)
