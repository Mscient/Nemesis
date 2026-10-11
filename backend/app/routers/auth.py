"""
routers/auth.py — Authentication endpoints for registration, login, and user profile.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token, hash_password, verify_password
from app.db.models import UserModel
from app.deps import get_current_user, get_db
from app.schemas import TokenResponse, UserLogin, UserOut, UserRegister

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    payload: UserRegister,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user account with email and password."""
    normalized_email = payload.email.strip().lower()
    
    # Check if user already exists
    existing = await db.execute(select(UserModel).where(UserModel.email == normalized_email))
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists.",
        )
    
    user = UserModel(
        email=normalized_email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name.strip() if payload.full_name else None,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    token = create_access_token(subject=user.email)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut.model_validate(user),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in and retrieve JWT token",
)
async def login(
    payload: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user with email and password and return access token."""
    normalized_email = payload.email.strip().lower()
    
    result = await db.execute(select(UserModel).where(UserModel.email == normalized_email))
    user = result.scalars().first()
    
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    token = create_access_token(subject=user.email)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserOut,
    summary="Get current user details",
)
async def get_me(
    current_user: UserModel = Depends(get_current_user),
):
    """Return profile details for the currently authenticated user."""
    return UserOut.model_validate(current_user)
