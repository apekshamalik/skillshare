from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.auth.auth_utils import verify_token
from src.schemas.user.user_schema import UserInDB
from typing import Dict

security = HTTPBearer()

# This will be imported from your router
def get_users_db() -> Dict[str, UserInDB]:
    """Get reference to the users database"""
    from src.routes.user.user_routes import users
    return users

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    users_db: Dict[str, UserInDB] = Depends(get_users_db)
) -> UserInDB:
    """
    Dependency to get the current authenticated user.
    """
    token = credentials.credentials
    payload = verify_token(token)
    
    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    
    user = users_db.get(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    return user