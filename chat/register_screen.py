import logging
import re

import flet as ft


class RegisterScreen(ft.Container):
    def __init__(self, chat_app):
        super().__init__()
        self.chat_app = chat_app

        # Configure logging
        self.logger = logging.getLogger("RegisterScreen")
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s:%(name)s: %(message)s"
        )
        handler.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(handler)

        # GUI components with validation helpers
        self.username = ft.TextField(
            label="Username",
            on_change=self.clear_field_error,
            on_submit=self.handle_enter_key,
        )
        self.username_help = ft.Text(
            "3-50 characters, letters, numbers, dots, hyphens, underscores only",
            size=12,
            color=ft.colors.GREY_600,
            no_wrap=False,
        )

        self.email = ft.TextField(
            label="Email",
            on_change=self.clear_field_error,
            on_submit=self.handle_enter_key,
        )
        self.email_help = ft.Text(
            "Valid email address required",
            size=12,
            color=ft.colors.GREY_600,
            no_wrap=False,
        )

        self.password = ft.TextField(
            label="Password",
            password=True,
            can_reveal_password=True,
            on_change=self.clear_field_error,
            on_submit=self.handle_enter_key,
        )
        self.password_help = ft.Text(
            "At least 8 characters with uppercase, lowercase, and number",
            size=12,
            color=ft.colors.GREY_600,
            no_wrap=False,
        )

        # Register button with loading state
        self.register_button = ft.ElevatedButton("Register", on_click=self.register)

        self.logger.info("RegisterScreen initialized")

    def build(self):
        """
        Builds the registration screen UI.
        """
        self.logger.info("Building registration screen UI")

        self.border_radius = 10
        self.padding = 30
        self.content = ft.Column(
            [
                ft.Text("Register", size=30),
                ft.Column([self.username, self.username_help], spacing=5),
                ft.Column([self.email, self.email_help], spacing=5),
                ft.Column([self.password, self.password_help], spacing=5),
                self.register_button,
                ft.TextButton(
                    "Already have an account? Login", on_click=self.show_login
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

    def validate_email(self, email):
        """
        Validates email format using regex.
        """
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(email_pattern, email) is not None

    def validate_password_strength(self, password):
        """
        Validates password strength requirements.
        Returns (is_valid, error_message)
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters"
        if len(password) > 128:
            return False, "Password must be less than 128 characters"

        has_upper = re.search(r"[A-Z]", password) is not None
        has_lower = re.search(r"[a-z]", password) is not None
        has_digit = re.search(r"\d", password) is not None

        if not has_upper:
            return False, "Password must contain at least one uppercase letter"
        if not has_lower:
            return False, "Password must contain at least one lowercase letter"
        if not has_digit:
            return False, "Password must contain at least one number"

        # Check for common weak passwords
        weak_patterns = [
            r"password",
            r"123456",
            r"qwerty",
            r"admin",
            r"guest",
            r"test",
            r"user",
            r"login",
            r"welcome",
            r"letmein",
        ]
        password_lower = password.lower()
        for pattern in weak_patterns:
            if re.search(pattern, password_lower):
                return (
                    False,
                    "Password is too common, please choose a stronger password",
                )

        return True, ""

    def validate_register_form(self):
        """
        Validates the registration form fields before submission.
        Returns True if valid, False otherwise.
        """
        is_valid = True

        # Clear previous errors
        self.username.error_text = None
        self.email.error_text = None
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
        elif self.username.value.strip().lower() in [
            "admin",
            "user",
            "test",
            "guest",
            "root",
            "administrator",
        ]:
            self.username.error_text = "Username is reserved, please choose another"
            is_valid = False

        # Validate email
        if not self.email.value or not self.email.value.strip():
            self.email.error_text = "Email is required"
            is_valid = False
        elif not self.validate_email(self.email.value.strip()):
            self.email.error_text = "Please enter a valid email address"
            is_valid = False
        elif len(self.email.value.strip()) > 254:
            self.email.error_text = "Email address is too long"
            is_valid = False

        # Validate password
        if not self.password.value:
            self.password.error_text = "Password is required"
            is_valid = False
        else:
            password_valid, password_error = self.validate_password_strength(
                self.password.value
            )
            if not password_valid:
                self.password.error_text = password_error
                is_valid = False

        # Update fields to show validation errors
        if not is_valid:
            self.username.update()
            self.email.update()
            self.password.update()
            self.logger.warning("Registration form validation failed")

        return is_valid

    def handle_enter_key(self, e):
        """
        Handles Enter key press in text fields to submit the form.
        """
        self.register(e)

    def register(self, e):
        """
        Handles the registration process when the register button is clicked.
        """
        # Validate form before making API call
        if not self.validate_register_form():
            return

        # Show loading state
        self.register_button.text = "Registering..."
        self.register_button.disabled = True
        self.register_button.update()

        try:
            username = self.username.value.strip()
            email = self.email.value.strip()
            password = self.password.value

            self.logger.info(f"Attempting registration for user: {username}")
            response = self.chat_app.api_client.register(username, email, password)
            if response.success:
                self.logger.info(f"Registration successful for user: {username}")
                self.show_success_dialog()
            else:
                error_message = f"Registration failed (Status {response.status_code})"
                self.logger.error(
                    f"Registration failed for user {username}: {error_message}\n{response.error}"
                )
                self.chat_app.show_error_dialog("Registration Error", response.error)
        finally:
            # Reset button state
            self.register_button.text = "Register"
            self.register_button.disabled = False
            self.register_button.update()

    def show_success_dialog(self):
        """
        Displays a success dialog after successful registration.
        """
        self.logger.info("Showing registration success dialog")

        def close_dlg(e):
            self.chat_app.page.close(dlg)
            self.chat_app.show_login()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Registration Successful"),
            content=ft.Text(
                "Your account has been created successfully. Please log in."
            ),
            actions=[ft.ElevatedButton("Go to Login", on_click=close_dlg)],
            actions_alignment=ft.MainAxisAlignment.CENTER,
            on_dismiss=close_dlg,
        )

        self.chat_app.page.open(dlg)

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
