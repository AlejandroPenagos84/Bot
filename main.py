import asyncio
import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from telegram.ext import Application, ApplicationBuilder

load_dotenv()  # antes de construir nada: auth y STOMP leen os.environ

from auth.api import AuthApi  # noqa: E402
from auth.http.app import mount_auth  # noqa: E402
from auth.http.container import build_container  # noqa: E402
from bot.application.use_cases.bot_actions import BotActionsService  # noqa: E402
from bot.application.use_cases.follow_user import FollowUserUseCase  # noqa: E402
from bot.application.use_cases.live_status_tracker import LiveStatusTracker  # noqa: E402
from bot.application.use_cases.monitor_users import MonitorUsersUseCase  # noqa: E402
from bot.application.use_cases.receive_ubication import ReceiveUbicationUseCase  # noqa: E402
from bot.infrastructure.conecction_manager import ConnectionManager  # noqa: E402
from bot.infrastructure.http_router import create_http_router  # noqa: E402
from bot.infrastructure.router import create_router  # noqa: E402
from bot.infrastructure.sqlite.database import SQLiteDatabase  # noqa: E402
from bot.infrastructure.sqlite.ubication_repository import SQLiteUbicationRepository  # noqa: E402
from bot.infrastructure.sqlite.user_repository import SQLiteUserRepository  # noqa: E402
from bot.infrastructure.status_connection_manager import StatusConnectionManager  # noqa: E402
from bot.infrastructure.stomp_source import StompSource  # noqa: E402
from bot.infrastructure.telegram.adapter import TelegramAdapter  # noqa: E402
from bot.infrastructure.telegram.messenger import TelegramMessenger  # noqa: E402

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError(
        "Falta BOT_TOKEN. Defínelo en .env o en las variables de entorno."
    )

# --- Auth ---
auth_container = build_container()
auth_api = AuthApi(auth_container.authenticate)  # fachada para el resto del monolito

# --- Bot ---
stomp = StompSource()
database = SQLiteDatabase(os.environ.get("DB_PATH", "bot.db"))
manager = ConnectionManager()
status_manager = StatusConnectionManager()
users = SQLiteUserRepository(database)
ubications = SQLiteUbicationRepository(database, users)

follow_user_use_case = FollowUserUseCase(stomp, ubications)
live_status = LiveStatusTracker(status_manager, ubications)
receive_ubication_use_case = ReceiveUbicationUseCase(ubications, manager, live_status)
monitor_users_use_case = MonitorUsersUseCase(users, ubications)

telegram_app: Application = ApplicationBuilder().token(BOT_TOKEN).build()
messenger = TelegramMessenger(telegram_app.bot)
actions = BotActionsService(
    users, ubications, follow_user_use_case, stomp, messenger, live_status
)
TelegramAdapter(telegram_app, messenger, actions).register()


@asynccontextmanager
async def lifespan(app: FastAPI):
    stomp.start(
        asyncio.get_running_loop(),
        receive_ubication_use_case.execute,
        receive_ubication_use_case.end_live,
    )

    await telegram_app.initialize()
    await telegram_app.start()
    if telegram_app.updater is not None:
        await telegram_app.updater.start_polling()

    try:
        yield
    finally:
        if telegram_app.updater is not None:
            await telegram_app.updater.stop()
        await telegram_app.stop()
        await telegram_app.shutdown()
        live_status.close()
        auth_container.close()


app = FastAPI(title="Bot de ubicaciones", lifespan=lifespan)
mount_auth(app, auth_container)
app.include_router(create_router(follow_user_use_case, manager, status_manager, auth_api))
app.include_router(create_http_router(monitor_users_use_case, auth_api))


def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
