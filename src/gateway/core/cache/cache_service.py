from datetime import datetime
from typing import Any, Protocol


class CacheService(Protocol):
    async def get(self, key: str) -> Any | None: ...

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int | None = None,
        expires_at: datetime | None = None,
    ) -> None: ...
