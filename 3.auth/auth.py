from fastapi import APIRouter, HTTPException, Depends, Header
from models import UserCreate
from security import verify_password, create_token, decode_token
from users import mock_users

router = APIRouter()

@router.post("/login")
def login(user: UserCreate):
    db_user = mock_users.get(user.username)
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="登录失败")
    token = create_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

@router.get("/me")
def get_profile(Authorization: str = Header(...)):
    if not Authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")
    token = Authorization.split(" ")[1]
    username = decode_token(token)
    if not username:
        raise HTTPException(status_code=403, detail="Token失效或非法")
    return {"msg": f"当前用户：{username}"}
