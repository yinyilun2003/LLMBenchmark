from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt
from datetime import datetime, timedelta

router = APIRouter()

SECRET_KEY = "demo-secret"
ALGORITHM = "HS256"

# 模拟用户
fake_users_db = {"test": "test"}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def create_token(username: str):
    payload = {
        "sub": username,
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if fake_users_db.get(form_data.username) != form_data.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(form_data.username)
    return {"access_token": token, "token_type": "bearer"}


def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"username": payload.get("sub")}
    except:
        raise HTTPException(status_code=401, detail="Invalid token")
