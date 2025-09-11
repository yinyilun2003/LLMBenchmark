import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
from routers.tasks import router as task_router
from auth import router as auth_router
from worker import worker_loop

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(worker_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        print("后台任务已终止")

app = FastAPI(title="任务系统 Demo", lifespan=lifespan)

# 注册路由
app.include_router(auth_router)
app.include_router(task_router)

# 可选 root 路由
@app.get("/")
def read_root():
    return {"message": "任务系统 API 启动成功"}




if __name__ == "__main__":
    uvicorn.run(app, port=8000)