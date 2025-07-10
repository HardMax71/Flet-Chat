import json
import os

import flet as ft

from .api_client import ApiClient
from .chat_list_screen import ChatListScreen
from .chat_screen import ChatScreen
from .login_screen import LoginScreen
from .register_screen import RegisterScreen
from .user_profile_screen import UserProfileScreen


class ChatApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Chat App"
        self.page.theme_mode = ft.ThemeMode.LIGHT

        api_part: str = os.environ.get("API_V1_STR", "/api/v1")
        self.api_client = ApiClient("http://localhost:8000/" + api_part)

        self.container = ft.Container(expand=True)
        self.page.add(self.container)

        self.show_login()

    def switch_screen(self, screen):
        self.container.content = screen
        self.page.update()

    def show_login(self):
        screen = LoginScreen(self)
        screen.build()
        self.switch_screen(screen)

    def show_register(self):
        screen = RegisterScreen(self)
        screen.build()
        self.switch_screen(screen)

    def show_chat_list(self):
        screen = ChatListScreen(self)
        screen.build()
        self.switch_screen(screen)

    def show_chat(self, chat_id):
        screen = ChatScreen(self, chat_id)
        screen.build()
        self.switch_screen(screen)

    def show_user_profile(self):
        screen = UserProfileScreen(self)
        screen.build()
        self.switch_screen(screen)

    # all funcs below are for processing str or dict with error message(s) inside
    def show_error_dialog(self, title, error):
        description = self._extract_error_message(error)
        self._display_error_dialog(title, description)

    def _extract_error_message(self, error) -> str:
        # Attempt to parse error if it's a string in JSON format
        if isinstance(error, str):
            error = self._parse_json_string(error)

        # Extract error message
        if isinstance(error, dict) and "detail" in error:
            return self._format_error_details(error["detail"])

        return str(error)

    def _parse_json_string(self, error_str: str) -> dict | str:
        try:
            return json.loads(error_str)
        except json.JSONDecodeError:
            return error_str

    def _format_error_details(self, detail: str | list) -> str:
        if isinstance(detail, list):
            messages = []
            for item in detail:
                field = self._get_field_name(item)
                message = item.get("msg", str(item))
                messages.append(f"- {field}: {message}")
            return "\n".join(messages)
        return detail

    def _get_field_name(self, item: dict) -> str:
        # Extract the field name, ignoring the "body" prefix if present
        if "loc" in item and len(item["loc"]) > 1:
            return item["loc"][-1]  # Take the last part of the location list
        return item.get("loc", ["Unknown field"])[-1]

    def _display_error_dialog(self, title, description):
        def close_dlg(e):
            self.page.close(dlg)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(title),
            content=ft.Text(description),
            actions=[ft.TextButton("OK", on_click=close_dlg)],
            actions_alignment=ft.MainAxisAlignment.END,
            on_dismiss=close_dlg,
        )

        self.page.open(dlg)