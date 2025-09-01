from fastapi import APIRouter, HTTPException
from models import UserCreate, User
from security import hash_password

router = APIRouter()
mock_users = {}  # username: User

@router.post("/register")
def register(user: UserCreate):
    if user.username in mock_users:
        raise HTTPException(status_code=400, detail="用户已存在")
    hashed = hash_password(user.password)
    mock_users[user.username] = User(username=user.username, hashed_password=hashed)
    return {"msg": "注册成功"}
