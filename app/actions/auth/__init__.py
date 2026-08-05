from __future__ import annotations

from app.actions.auth.logout import logout
from app.actions.auth.show_forgot_password import show_forgot_password
from app.actions.auth.show_login import show_login
from app.actions.auth.show_register import show_register
from app.actions.auth.show_reset_password import show_reset_password
from app.actions.auth.submit_forgot_password import submit_forgot_password
from app.actions.auth.submit_login import submit_login
from app.actions.auth.submit_register import submit_register
from app.actions.auth.submit_reset_password import submit_reset_password


route_handlers = [
    show_login,
    submit_login,
    show_register,
    submit_register,
    show_forgot_password,
    submit_forgot_password,
    show_reset_password,
    submit_reset_password,
    logout,
]