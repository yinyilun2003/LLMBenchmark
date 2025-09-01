import uvicorn
from fastapi import FastAPI
from users import router as user_router
from auth import router as auth_router

app = FastAPI(title="Mock 用户系统 + JWT 鉴权")

app.include_router(user_router, prefix="/users", tags=["用户"])
app.include_router(auth_router, prefix="/auth", tags=["登录鉴权"])

if __name__ == "__main__":
    uvicorn.run(app, port=8000)