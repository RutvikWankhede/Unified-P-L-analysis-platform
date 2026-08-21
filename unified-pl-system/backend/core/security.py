from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
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


# Enterprise RBAC Hierarchy mapping
ROLE_HIERARCHY = {
    "ADMINISTRATOR": ["ADMINISTRATOR", "FINANCE_MANAGER", "DEPARTMENT_HEAD", "AUDITOR", "EMPLOYEE", "Viewer"],
    "FINANCE_MANAGER": ["FINANCE_MANAGER", "DEPARTMENT_HEAD", "AUDITOR", "EMPLOYEE", "Viewer"],
    "DEPARTMENT_HEAD": ["DEPARTMENT_HEAD", "EMPLOYEE", "Viewer"],
    "AUDITOR": ["AUDITOR", "Viewer"],
    "EMPLOYEE": ["EMPLOYEE", "Viewer"],
    "Admin": ["ADMINISTRATOR", "FINANCE_MANAGER", "DEPARTMENT_HEAD", "AUDITOR", "EMPLOYEE", "Viewer"],  # Legacy compat
    "Finance": ["FINANCE_MANAGER", "DEPARTMENT_HEAD", "AUDITOR", "EMPLOYEE", "Viewer"],  # Legacy compat
    "Manager": ["DEPARTMENT_HEAD", "EMPLOYEE", "Viewer"],  # Legacy compat
    "Viewer": ["Viewer"]
}

def require_role(allowed_roles: list[str]):
    def role_checker(current_user: User = Depends(get_current_user)):
        user_role = current_user.role or "Viewer"
        has_permission = False
        
        # Check if user's role grants them any of the allowed roles
        user_capabilities = ROLE_HIERARCHY.get(user_role, [])
        for allowed in allowed_roles:
            if allowed in user_capabilities:
                has_permission = True
                break
                
        if not has_permission:
            raise HTTPException(status_code=403, detail="Not enough permissions. Requires one of: " + ", ".join(allowed_roles))
        return current_user

    return role_checker
