from bot.application.ports.ports import UbicationRepository
from bot.domain.ubication import Ubication


class UbicationMemoryRepository(UbicationRepository):
    def __init__(self):
        self.ubications: dict[int, list[Ubication]] = {}

    async def save_last(self, user_id: int, ubication: Ubication):
        self.ubications.setdefault(user_id, []).append(ubication)

    async def get_last(self, user_id: int):
        history = self.ubications.get(user_id)
        return history[-1] if history else None

    async def end_live(self, user_id: int) -> None:
        history = self.ubications.get(user_id)
        if history:
            history[-1] = history[-1].ended()
