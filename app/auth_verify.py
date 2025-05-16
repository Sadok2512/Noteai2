from fastapi import Depends, HTTPException, status, Header
from jose import JWTError, jwt
import os

SECRET_KEY = os.getenv("JWT_SECRET", "secret123")
ALGORITHM = "HS256"

def verify_token(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload  # e.g. contains user_id
    except JWTError:
        raise HTTPException(status_code=403, detail="Token is invalid or expired")

# Sample usage inside a route:
from fastapi import APIRouter

router = APIRouter()

@router.get("/auth/verify")
def verify_user(payload: dict = Depends(verify_token)):
    return {"valid": True, "payload": payload}