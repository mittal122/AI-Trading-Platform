from fastapi import APIRouter, Depends, HTTPException, Request

from backend.app.api.deps import get_current_user
from backend.app.core.rate_limit import limiter
from backend.app.db.models import User
from backend.app.schemas.auth import (
    ApiKeyCreatedResponse,
    ApiKeyCreateRequest,
    ApiKeyListResponse,
    ApiKeyResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from backend.app.services.auth.auth_service import AuthError, auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
@limiter.limit("10/minute")
async def register(request: Request, req: RegisterRequest) -> UserResponse:
    try:
        user = await auth_service.register(req.email, req.password)
    except AuthError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, req: LoginRequest) -> TokenResponse:
    try:
        return await auth_service.login(req.email, req.password)
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/refresh", response_model=TokenResponse)
async def refresh(req: RefreshRequest) -> TokenResponse:
    try:
        return await auth_service.refresh(req.refresh_token)
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(user)


@router.post("/api-keys", response_model=ApiKeyCreatedResponse, status_code=201)
async def create_api_key(
    req: ApiKeyCreateRequest, user: User = Depends(get_current_user)
) -> ApiKeyCreatedResponse:
    record, raw_key = await auth_service.create_api_key(user.id, req.name)
    return ApiKeyCreatedResponse(
        id=record.id,
        name=record.name,
        key=raw_key,
        key_prefix=record.key_prefix,
        created_at=record.created_at,
    )


@router.get("/api-keys", response_model=ApiKeyListResponse)
async def list_api_keys(user: User = Depends(get_current_user)) -> ApiKeyListResponse:
    keys = await auth_service.list_api_keys(user.id)
    return ApiKeyListResponse(keys=[ApiKeyResponse.model_validate(k) for k in keys])


@router.delete("/api-keys/{key_id}", status_code=204)
async def revoke_api_key(key_id: int, user: User = Depends(get_current_user)) -> None:
    ok = await auth_service.revoke_api_key(user.id, key_id)
    if not ok:
        raise HTTPException(status_code=404, detail="API key not found")
