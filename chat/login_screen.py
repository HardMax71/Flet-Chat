import flet as ft


class LoginScreen(ft.UserControl):
    def __init__(self, chat_app):
        super().__init__()
        self.chat_app = chat_app

    def build(self):
        self.username = ft.TextField(label="Username")
        self.password = ft.TextField(label="Password", password=True, can_reveal_password=True)

        return ft.Container(
            border_radius=10,
            padding=30,
            content=ft.Column(
                [
                    ft.Text("Login", size=30),
                    self.username,
                    self.password,
                    ft.ElevatedButton("Login", on_click=self.login),
                    ft.TextButton("Don't have an account? Register", on_click=self.show_register)
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=20
            )
        )

    def login(self, e):
        response = self.chat_app.api_client.login(self.username.value, self.password.value)
        if response.success:
            self.chat_app.show_chat_list()
        else:
            error_message = f"Login failed (Status {response.status_code})"
            self.chat_app.show_error_dialog("Login Error", f"{error_message}\n\n{response.error}")

    def show_register(self, e):
        self.chat_app.show_register()
