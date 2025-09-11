from fastapi import APIRouter, HTTPException
from models.schemas import UserSignup, UserLogin, UserResponse

router = APIRouter()