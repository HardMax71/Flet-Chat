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
        self.switch_screen(LoginScreen(self))

    def show_register(self):
        self.switch_screen(RegisterScreen(self))

    def show_chat_list(self):
        self.switch_screen(ChatListScreen(self))

    def show_chat(self, chat_id):
        self.switch_screen(ChatScreen(self, chat_id))

    def show_user_profile(self):
        self.switch_screen(UserProfileScreen(self))

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
            dlg.open = False
            self.page.update()

        dlg = ft.AlertDialog(
            title=ft.Text(title),
            content=ft.Text(description),
            actions=[ft.TextButton("OK", on_click=close_dlg)],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self.page.dialog = dlg
        dlg.open = True
        self.page.update()