from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    from jose import JWTError, jwt

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user


# Enterprise RBAC Hierarchy mapping (case-insensitive)
ROLE_HIERARCHY = {
    "ADMINISTRATOR": ["ADMINISTRATOR", "ADMIN", "FINANCE_MANAGER", "DEPARTMENT_HEAD", "AUDITOR", "EMPLOYEE", "VIEWER"],
    "ADMIN": ["ADMINISTRATOR", "ADMIN", "FINANCE_MANAGER", "DEPARTMENT_HEAD", "AUDITOR", "EMPLOYEE", "VIEWER"],
    "FINANCE_MANAGER": ["FINANCE_MANAGER", "FINANCE", "DEPARTMENT_HEAD", "AUDITOR", "EMPLOYEE", "VIEWER"],
    "FINANCE": ["FINANCE_MANAGER", "FINANCE", "DEPARTMENT_HEAD", "AUDITOR", "EMPLOYEE", "VIEWER"],
    "DEPARTMENT_HEAD": ["DEPARTMENT_HEAD", "MANAGER", "EMPLOYEE", "VIEWER"],
    "MANAGER": ["DEPARTMENT_HEAD", "MANAGER", "EMPLOYEE", "VIEWER"],
    "AUDITOR": ["AUDITOR", "VIEWER"],
    "EMPLOYEE": ["EMPLOYEE", "VIEWER"],
    "VIEWER": ["VIEWER"]
}

def require_role(allowed_roles: list[str]):
    normalized_allowed = [r.upper() for r in allowed_roles]
    
    def role_checker(current_user: User = Depends(get_current_user)):
        user_role = (current_user.role or "Viewer").strip().upper()
        user_capabilities = ROLE_HIERARCHY.get(user_role, [user_role])
        
        # Admin / Administrator has universal access
        if "ADMINISTRATOR" in user_capabilities or "ADMIN" in user_capabilities or user_role in ("ADMIN", "ADMINISTRATOR"):
            return current_user
            
        for allowed in normalized_allowed:
            if allowed in user_capabilities or user_role == allowed:
                return current_user
                
        raise HTTPException(status_code=403, detail="Not enough permissions. Requires one of: " + ", ".join(allowed_roles))

    return role_checker
