from __future__ import annotations

from typing import Protocol


class EmailSenderContract(Protocol):
    async def send_password_reset_email(
        self,
        *,
        to_email: str,
        reset_url: str,
    ) -> None:
        ...