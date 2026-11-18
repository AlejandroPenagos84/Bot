from dataclasses import dataclass
import datetime


@dataclass(frozen=True)
class Identity:
    user_id: str
    username: str
    email: str
    role: str  # 'admin' | 'user'
    expires_at: datetime.datetime

    @property
    def is_admin(self) -> bool:
        return self.role == 'admin'
