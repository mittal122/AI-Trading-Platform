from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import ApiKey, User


class UserRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user: User) -> User:
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email.lower())
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> User | None:
        return await self._session.get(User, user_id)

    async def update_tier(self, user: User, tier: str) -> User:
        user.tier = tier
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def update_stripe_ids(
        self, user: User, customer_id: str | None = None, subscription_id: str | None = None
    ) -> User:
        if customer_id is not None:
            user.stripe_customer_id = customer_id
        if subscription_id is not None:
            user.stripe_subscription_id = subscription_id
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def get_by_stripe_customer_id(self, customer_id: str) -> User | None:
        stmt = select(User).where(User.stripe_customer_id == customer_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()


class ApiKeyRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, api_key: ApiKey) -> ApiKey:
        self._session.add(api_key)
        await self._session.commit()
        await self._session.refresh(api_key)
        return api_key

    async def get_by_hash(self, key_hash: str) -> ApiKey | None:
        stmt = select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active == 1)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_for_user(self, user_id: int) -> list[ApiKey]:
        stmt = select(ApiKey).where(ApiKey.user_id == user_id).order_by(ApiKey.created_at.desc())
        return list((await self._session.execute(stmt)).scalars().all())

    async def get_for_user(self, key_id: int, user_id: int) -> ApiKey | None:
        stmt = select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def revoke(self, api_key: ApiKey) -> None:
        api_key.is_active = 0
        await self._session.commit()

    async def touch_last_used(self, api_key: ApiKey) -> None:
        from datetime import datetime, timezone

        api_key.last_used_at = datetime.now(timezone.utc)
        await self._session.commit()
