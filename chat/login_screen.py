import logging
import re

import flet as ft


class LoginScreen(ft.Container):
    def __init__(self, chat_app):
        super().__init__()
        self.chat_app = chat_app

        # Configure logging
        self.logger = logging.getLogger("LoginScreen")
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s:%(name)s: %(message)s"
        )
        handler.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(handler)

        # Initialize UI components
        self.username = ft.TextField(
            label="Username",
            on_change=self.clear_field_error,
            on_submit=self.handle_enter_key,
            helper_text="Username must be at least 3 characters",
        )
        self.password = ft.TextField(
            label="Password",
            password=True,
            can_reveal_password=True,
            on_change=self.clear_field_error,
            on_submit=self.handle_enter_key,
            helper_text="Password must be at least 8 characters",
        )

        # Login button with loading state
        self.login_button = ft.ElevatedButton("Login", on_click=self.login)

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
                self.login_button,
                ft.TextButton(
                    "Don't have an account? Register", on_click=self.show_register
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20,
        )

    def clear_field_error(self, e):
        """
        Clears error state when user starts typing.
        """
        if hasattr(e.control, "error_text") and e.control.error_text:
            e.control.error_text = None
            e.control.update()

    def validate_login_form(self):
        """
        Validates the login form fields before submission.
        Returns True if valid, False otherwise.
        """
        is_valid = True

        # Clear previous errors
        self.username.error_text = None
        self.password.error_text = None

        # Validate username
        if not self.username.value or not self.username.value.strip():
            self.username.error_text = "Username is required"
            is_valid = False
        elif len(self.username.value.strip()) < 3:
            self.username.error_text = "Username must be at least 3 characters"
            is_valid = False
        elif len(self.username.value.strip()) > 50:
            self.username.error_text = "Username must be less than 50 characters"
            is_valid = False
        elif not re.match(r"^[a-zA-Z0-9_.-]+$", self.username.value.strip()):
            self.username.error_text = "Username can only contain letters, numbers, dots, hyphens, and underscores"
            is_valid = False

        # Validate password
        if not self.password.value:
            self.password.error_text = "Password is required"
            is_valid = False
        elif len(self.password.value) < 8:
            self.password.error_text = "Password must be at least 8 characters"
            is_valid = False
        elif len(self.password.value) > 128:
            self.password.error_text = "Password must be less than 128 characters"
            is_valid = False

        # Update fields to show validation errors
        if not is_valid:
            self.username.update()
            self.password.update()
            self.logger.warning("Login form validation failed")

        return is_valid

    def handle_enter_key(self, e):
        """
        Handles Enter key press in text fields to submit the form.
        """
        self.login(e)

    def login(self, e):
        """
        Handles the login process when the login button is clicked.
        """
        # Validate form before making API call
        if not self.validate_login_form():
            return

        # Show loading state
        self.login_button.text = "Logging in..."
        self.login_button.disabled = True
        self.login_button.update()

        try:
            username = self.username.value.strip()
            password = self.password.value

            self.logger.info(f"Attempting login for user: {username}")
            response = self.chat_app.api_client.login(username, password)
            if response.success:
                self.logger.info(f"Login successful for user: {username}")
                # Get user data and use centralized login handling
                user_response = self.chat_app.api_client.get_current_user()
                if user_response.success:
                    self.chat_app.handle_successful_login(user_response.data)
                else:
                    # Fallback to showing chat list if user data fetch fails
                    self.chat_app.show_chat_list()
            else:
                error_message = f"Login failed (Status {response.status_code})"
                self.logger.error(
                    f"Login failed for user {username}: {error_message}\n{response.error}"
                )
                self.chat_app.show_error_dialog("Login Error", response.error)
        finally:
            # Reset button state
            self.login_button.text = "Login"
            self.login_button.disabled = False
            self.login_button.update()

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
