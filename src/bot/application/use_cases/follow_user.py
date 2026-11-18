import asyncio

from bot.application.ports.ports import UbicationRepository, UbicationSourcePort
from bot.domain.ubication import Ubication


class FollowUserUseCase:
    def __init__(self, source: UbicationSourcePort, repo: UbicationRepository) -> None:
        self._source = source
        self._repo = repo
        self._followers: dict[int, int] = {}
        self._lock = asyncio.Lock()
        
    async def follow_user(self, user_id: int) -> Ubication | None:
        async with self._lock: # Protect the shared state
            if self._followers.get(user_id,0) == 0: # If no one is following this user, subscribe to the source
                if not await self._source.suscribe(user_id):
                    raise Exception(f"Failed to subscribe to user {user_id}")
            self._followers[user_id] = self._followers.get(user_id, 0) + 1
        return await self._repo.get_last(user_id)
    
    async def is_following(self, user_id: int) -> bool:
        async with self._lock:
            return self._followers.get(user_id, 0) > 0

    async def unfollow_user(self, user_id: int) -> None:
        async with self._lock:
            rest = self._followers.get(user_id, 0) - 1
            if rest <= 0:
                if not await self._source.unsubscribe(user_id):
                    raise Exception(f"Failed to unsubscribe from user {user_id}")
                self._followers.pop(user_id, None)
            else:
                self._followers[user_id] = rest