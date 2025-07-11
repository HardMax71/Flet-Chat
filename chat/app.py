import logging
import os
from typing import Any

import flet as ft

from .api_client import ApiClient
from .chat_list_screen import ChatListScreen
from .chat_screen import ChatScreen
from .login_screen import LoginScreen
from .register_screen import RegisterScreen
from .state_manager import AppState, StateEvent, StateManager
from .user_profile_screen import UserProfileScreen


class ChatApp:
    def __init__(self, page: ft.Page) -> None:
        self.page: ft.Page = page
        self.page.title = "Chat App"
        self.page.theme_mode = ft.ThemeMode.LIGHT

        self.logger: logging.Logger = logging.getLogger("ChatApp")
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s:%(name)s: %(message)s"
        )
        handler.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(handler)

        api_part: str = os.environ.get("API_V1_STR", "/api/v1")
        self.api_client: ApiClient = ApiClient("http://localhost:8000/" + api_part)

        self.state_manager: StateManager = StateManager(self.api_client)
        self.app_state: AppState = AppState()
        self.app_state.subscribe(StateEvent.USER_LOGGED_IN, self._on_user_logged_in)
        self.app_state.subscribe(StateEvent.USER_LOGGED_OUT, self._on_user_logged_out)

        self.container: ft.Container = ft.Container(expand=True)
        self.page.add(self.container)

        self.state_manager.initialize()
        if self.app_state.is_authenticated:
            self.logger.info("User already authenticated, showing chat list")
            self.show_chat_list()
        else:
            self.show_login()

    def _on_user_logged_in(self, data: dict[str, Any]) -> None:
        self.logger.info("User logged in, updating UI")
        # UI will be updated by screens subscribing to state changes

    def _on_user_logged_out(self, data: dict[str, Any]) -> None:
        self.logger.info("User logged out, showing login screen")
        self.show_login()

    def switch_screen(self, screen: ft.Control) -> None:
        self.container.content = screen
        self.page.update()

    def show_login(self) -> None:
        self.state_manager.set_current_chat(None)
        screen = LoginScreen(self)
        screen.build()
        self.switch_screen(screen)

    def show_register(self) -> None:
        screen = RegisterScreen(self)
        screen.build()
        self.switch_screen(screen)

    def show_chat_list(self) -> None:
        self.state_manager.set_current_chat(None)
        screen = ChatListScreen(self)
        screen.build()
        self.switch_screen(screen)

    def show_chat(self, chat_id: int) -> None:
        self.state_manager.set_current_chat(chat_id)
        screen = ChatScreen(self, chat_id)
        screen.build()
        self.switch_screen(screen)

    def show_user_profile(self) -> None:
        screen = UserProfileScreen(self)
        screen.build()
        self.switch_screen(screen)

    def handle_successful_login(self, user_data: dict[str, Any]) -> None:
        self.logger.info(
            f"Handling successful login for user: {user_data.get('username', 'Unknown')}"
        )
        self.state_manager.login_user(user_data)
        self.show_chat_list()

    def handle_logout(self) -> None:
        self.logger.info("Handling user logout")
        self.state_manager.logout_user()
        # UI will be updated by _on_user_logged_out observer

    def refresh_chats(self) -> bool:
        return self.state_manager.refresh_chats()

    def show_error_dialog(self, title: str, error: Any) -> None:
        """Display an error dialog, converting any error to string."""

        def close_dlg(_: ft.ControlEvent) -> None:
            self.page.close(dlg)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(title),
            content=ft.Text(str(error)),
            actions=[ft.TextButton("OK", on_click=close_dlg)],
            actions_alignment=ft.MainAxisAlignment.END,
            on_dismiss=close_dlg,
        )

        self.page.open(dlg)
