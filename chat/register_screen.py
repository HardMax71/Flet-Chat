import flet as ft


class RegisterScreen(ft.UserControl):
    def __init__(self, chat_app):
        super().__init__()
        self.chat_app = chat_app

    def build(self):
        self.username = ft.TextField(label="Username")
        self.email = ft.TextField(label="Email")
        self.password = ft.TextField(label="Password", password=True, can_reveal_password=True)

        return ft.Container(
            border_radius=10,
            padding=30,
            content=ft.Column(
                [
                    ft.Text("Register", size=30),
                    self.username,
                    self.email,
                    self.password,
                    ft.ElevatedButton("Register", on_click=self.register),
                    ft.TextButton("Already have an account? Login", on_click=self.show_login)
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=20
            )
        )

    def register(self, e):
        response = self.chat_app.api_client.register(self.username.value, self.email.value, self.password.value)
        if response.success:
            self.show_success_dialog()
        else:
            error_message = f"Registration failed (Status {response.status_code})"
            self.chat_app.show_error_dialog("Registration Error", f"{error_message}\n\n{response.error}")

    def show_success_dialog(self):
        def close_dlg(e):
            dlg.open = False
            self.chat_app.page.update()
            self.chat_app.show_login()

        dlg = ft.AlertDialog(
            title=ft.Text("Registration Successful"),
            content=ft.Text("Your account has been created successfully. Please log in."),
            actions=[
                ft.ElevatedButton("Go to Login", on_click=close_dlg)
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER,
        )

        self.chat_app.page.dialog = dlg
        dlg.open = True
        self.chat_app.page.update()

    def show_login(self, e):
        self.chat_app.show_login()
