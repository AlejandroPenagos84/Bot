from datetime import datetime

from bot.application.ports.ports import UbicationNotifier, UbicationRepository
from bot.application.use_cases.live_status_tracker import LiveStatusTracker
from bot.domain.ubication import Ubication


class ReceiveUbicationUseCase:
    def __init__(
        self,
        repo: UbicationRepository,
        notifier: UbicationNotifier,
        live_status: LiveStatusTracker,
    ) -> None:
        self._repo = repo
        self._notifier = notifier
        self._live_status = live_status

    async def execute(self, user_id: int, ubication: Ubication) -> None:
        await self._repo.save_last(user_id, ubication)
        await self._notifier.notify(user_id, ubication)
        await self._live_status.on_ubication(user_id, ubication)

    async def end_live(self, user_id: int, ended_at: datetime) -> None:
        await self._repo.end_live(user_id)
        await self._notifier.notify_live_ended(user_id, ended_at)
        await self._live_status.on_live_ended(user_id, ended_at)
