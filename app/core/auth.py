from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
import jwt
from app.core.config import settings
from typing import Optional

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

async def get_current_user_token(request: Request):
    # Tenta pegar do header Authorization: Bearer <token>
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]
    
    # Tenta pegar do cookie auth_token
    cookie_token = request.cookies.get("auth_token")
    if cookie_token:
        return cookie_token
        
    return None

async def get_current_user_payload(token: Optional[str] = Depends(get_current_user_token)):
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256", "HS384", "HS512"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user_id(payload: dict = Depends(get_current_user_payload)) -> int:
    try:
        user_id = int(payload.get("sub"))
        return user_id
    except (ValueError, TypeError):
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        )
