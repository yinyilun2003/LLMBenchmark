from fastapi import APIRouter, HTTPException
from api.models.schemas import UserSignup, UserLogin, UserResponse

router = APIRouter()