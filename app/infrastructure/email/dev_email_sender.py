from __future__ import annotations


class DevEmailSender:
    async def send_password_reset_email(
        self,
        *,
        to_email: str,
        reset_url: str,
    ) -> None:
        print("")
        print("=== Gravewright password reset ===")
        print(f"To: {to_email}")
        print(f"Reset URL: {reset_url}")
        print("==================================")
        print("")