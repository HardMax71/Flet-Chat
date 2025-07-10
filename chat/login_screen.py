import logging
import flet as ft

class LoginScreen(ft.Container):
    def __init__(self, chat_app):
        super().__init__()
        self.chat_app = chat_app

        # Configure logging
        self.logger = logging.getLogger('LoginScreen')
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s:%(name)s: %(message)s')
        handler.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(handler)

        # Initialize UI components
        self.username = ft.TextField(label="Username")
        self.password = ft.TextField(label="Password", password=True, can_reveal_password=True)

    def build(self):
        """
        Builds the login screen UI.
        """
        self.logger.info("Building login screen UI")
        
        self.border_radius = 10
        self.padding = 30
        self.content = ft.Column(
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

    def login(self, e):
        """
        Handles the login process when the login button is clicked.
        """
        self.logger.info(f"Attempting login for user: {self.username.value}")
        response = self.chat_app.api_client.login(self.username.value, self.password.value)
        if response.success:
            self.logger.info(f"Login successful for user: {self.username.value}")
            self.chat_app.show_chat_list()
        else:
            error_message = f"Login failed (Status {response.status_code})"
            self.logger.error(f"Login failed for user {self.username.value}: {error_message}\n{response.error}")
            self.chat_app.show_error_dialog("Login Error", response.error)

    def show_register(self, e):
        """
        Navigates to the registration screen.
        """
        self.logger.info("Navigating to registration screen")
        self.chat_app.show_register()

    def did_mount(self):
        """
        Called when the control is added to the page.
        """
        self.logger.info("LoginScreen mounted")

    def will_unmount(self):
        """
        Called when the control is about to be removed from the page.
        """
        self.logger.info("LoginScreen will unmount")