import logging

import flet as ft


class RegisterScreen(ft.Column):
    def __init__(self, chat_app):
        super().__init__()
        self.isolated = True
        self.chat_app = chat_app

        # Configure logging
        self.logger = logging.getLogger('RegisterScreen')
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s:%(name)s: %(message)s')
        handler.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(handler)

        # GUI components
        self.username = ft.TextField(label="Username")
        self.email = ft.TextField(label="Email")
        self.password = ft.TextField(label="Password", password=True, can_reveal_password=True)

        self.logger.info("RegisterScreen initialized")

    def build(self):
        """
        Builds the registration screen UI.
        """
        self.logger.info("Building registration screen UI")
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
        """
        Handles the registration process when the register button is clicked.
        """
        self.logger.info(f"Attempting registration for user: {self.username.value}")
        response = self.chat_app.api_client.register(self.username.value, self.email.value, self.password.value)
        if response.success:
            self.logger.info(f"Registration successful for user: {self.username.value}")
            self.show_success_dialog()
        else:
            error_message = f"Registration failed (Status {response.status_code})"
            self.logger.error(f"Registration failed for user {self.username.value}: {error_message}\n{response.error}")
            self.chat_app.show_error_dialog("Registration Error", f"{error_message}\n\n{response.error}")

    def show_success_dialog(self):
        """
        Displays a success dialog after successful registration.
        """
        self.logger.info("Showing registration success dialog")

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
        """
        Navigates to the login screen.
        """
        self.logger.info("Navigating to login screen")
        self.chat_app.show_login()

    def did_mount(self):
        """
        Called when the control is added to the page.
        """
        self.logger.info("RegisterScreen mounted")

    def will_unmount(self):
        """
        Called when the control is about to be removed from the page.
        """
        self.logger.info("RegisterScreen will unmount")
