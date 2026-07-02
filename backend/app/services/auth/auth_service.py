"""AuthService — registration, login, token refresh, API key issuance."""

from backend.app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_api_key,
    hash_api_key,
    hash_password,
    verify_password,
)
from backend.app.db.database import AsyncSessionLocal
from backend.app.db.models import ApiKey, User
from backend.app.db.repository.user_repo import ApiKeyRepository, UserRepository
from backend.app.schemas.auth import TokenResponse


class AuthError(Exception):
    pass


class AuthService:

    async def register(self, email: str, password: str) -> User:
        email = email.lower()
        async with AsyncSessionLocal() as session:
            repo = UserRepository(session)
            if await repo.get_by_email(email) is not None:
                raise AuthError("Email already registered")
            user = User(email=email, hashed_password=hash_password(password))
            return await repo.create(user)

    async def login(self, email: str, password: str) -> TokenResponse:
        async with AsyncSessionLocal() as session:
            repo = UserRepository(session)
            user = await repo.get_by_email(email.lower())
            if user is None or not verify_password(password, user.hashed_password):
                raise AuthError("Invalid email or password")
            if not user.is_active:
                raise AuthError("Account is disabled")
            return TokenResponse(
                access_token=create_access_token(user.id, user.email, user.tier),
                refresh_token=create_refresh_token(user.id),
            )

    async def refresh(self, refresh_token: str) -> TokenResponse:
        payload = decode_token(refresh_token)
        if payload is None or payload.get("type") != "refresh":
            raise AuthError("Invalid or expired refresh token")

        user_id = int(payload["sub"])
        async with AsyncSessionLocal() as session:
            repo = UserRepository(session)
            user = await repo.get_by_id(user_id)
            if user is None or not user.is_active:
                raise AuthError("User not found or disabled")
            return TokenResponse(
                access_token=create_access_token(user.id, user.email, user.tier),
                refresh_token=create_refresh_token(user.id),
            )

    async def get_user_by_id(self, user_id: int) -> User | None:
        async with AsyncSessionLocal() as session:
            repo = UserRepository(session)
            return await repo.get_by_id(user_id)

    # ------------------------------------------------------------------
    # API keys
    # ------------------------------------------------------------------

    async def create_api_key(self, user_id: int, name: str) -> tuple[ApiKey, str]:
        raw_key = generate_api_key()
        async with AsyncSessionLocal() as session:
            repo = ApiKeyRepository(session)
            record = ApiKey(
                user_id=user_id,
                name=name,
                key_hash=hash_api_key(raw_key),
                key_prefix=raw_key[:16],
            )
            saved = await repo.create(record)
            return saved, raw_key

    async def list_api_keys(self, user_id: int) -> list[ApiKey]:
        async with AsyncSessionLocal() as session:
            repo = ApiKeyRepository(session)
            return await repo.list_for_user(user_id)

    async def revoke_api_key(self, user_id: int, key_id: int) -> bool:
        async with AsyncSessionLocal() as session:
            repo = ApiKeyRepository(session)
            key = await repo.get_for_user(key_id, user_id)
            if key is None:
                return False
            await repo.revoke(key)
            return True

    async def authenticate_api_key(self, raw_key: str) -> User | None:
        key_hash = hash_api_key(raw_key)
        async with AsyncSessionLocal() as session:
            key_repo = ApiKeyRepository(session)
            key = await key_repo.get_by_hash(key_hash)
            if key is None:
                return None
            await key_repo.touch_last_used(key)

            user_repo = UserRepository(session)
            user = await user_repo.get_by_id(key.user_id)
            if user is None or not user.is_active:
                return None
            return user


auth_service = AuthService()
