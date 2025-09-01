import uvicorn
from fastapi import FastAPI
from routers import user, task, log

app = FastAPI()

app.include_router(user.router, prefix="/api/user", tags=["User"])
app.include_router(task.router, prefix="/api/task", tags=["Task"])
app.include_router(log.router, prefix="/api/logs", tags=["Log"])

if __name__ == "__main__":
    uvicorn.run(app, port=8000)