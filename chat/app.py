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

    def show_error_dialog(self, title, description):
        def close_dlg(e):
            dlg.open = False
            self.page.update()

        dlg = ft.AlertDialog(
            title=ft.Text(title),
            content=ft.Text(description),
            actions=[
                ft.TextButton("OK", on_click=close_dlg)
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self.page.dialog = dlg
        dlg.open = True
        self.page.update()
