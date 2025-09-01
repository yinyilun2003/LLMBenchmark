from fastapi import APIRouter, HTTPException
from models.schemas import UserSignup, UserLogin, UserResponse
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

router = APIRouter()

fake_users_db = {}

@router.post("/signup", response_model=UserResponse)
def signup(user: UserSignup):
    if user.username in fake_users_db:
        raise HTTPException(status_code=400, detail="User already exists.")
    fake_users_db[user.username] = {
        "username": user.username,
        "email": user.email,
        "hashed_password": hash_password(user.password)
    }
    return UserResponse(username=user.username, email=user.email)

@router.post("/login")
def login(user: UserLogin):
    if user.username not in fake_users_db:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    db_user = fake_users_db[user.username]
    if not verify_password(user.password, db_user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": "fake-jwt-token", "username": user.username}