import logging
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db, Base, engine
from app.auth import verify_password, get_password_hash, create_access_token, get_user_by_username
from app import models, schemas

logger = logging.getLogger("talkbuddy.auth")
router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    clean_username = user_data.username.strip()
    try:
        # Check if username exists
        existing_user = get_user_by_username(db, clean_username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
            
        # Create new user
        hashed_password = get_password_hash(user_data.password)
        db_user = models.User(
            username=clean_username,
            hashed_password=hashed_password
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        logger.info(f"User '{clean_username}' registered successfully (id={db_user.id}).")
        return db_user
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        err_msg = str(e)
        logger.error(f"Registration failed for '{clean_username}': {err_msg}", exc_info=True)

        # If table does not exist, attempt to auto-create tables and retry once
        if "does not exist" in err_msg or "no such table" in err_msg:
            try:
                logger.info("Attempting auto-creation of missing database tables...")
                Base.metadata.create_all(bind=engine)
                hashed_password = get_password_hash(user_data.password)
                db_user = models.User(
                    username=clean_username,
                    hashed_password=hashed_password
                )
                db.add(db_user)
                db.commit()
                db.refresh(db_user)
                logger.info(f"User '{clean_username}' created after table auto-creation.")
                return db_user
            except Exception as retry_err:
                db.rollback()
                logger.error(f"Retry after table creation failed: {retry_err}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database setup error: {str(retry_err)}"
                )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {err_msg}"
        )

@router.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    try:
        user = get_user_by_username(db, form_data.username.strip())
        if not user or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        access_token = create_access_token(
            data={"sub": user.username, "id": user.id}
        )
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed for user '{form_data.username}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )

