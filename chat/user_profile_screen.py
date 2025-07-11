import logging

import flet as ft


class UserProfileScreen(ft.Column):
    def __init__(self, chat_app):
        super().__init__()
        self.chat_app = chat_app

        # Configure logging
        self.logger = logging.getLogger("UserProfileScreen")
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s:%(name)s: %(message)s"
        )
        handler.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(handler)

        self.logger.info("UserProfileScreen initialized")

    def build(self):
        """
        Builds the user profile screen UI.
        """
        self.logger.info("Building user profile screen UI")
        response = self.chat_app.api_client.get_current_user()
        if response.success:
            self.user_data = response.data
            self.username = ft.TextField(
                label="Username", value=self.user_data["username"]
            )
            self.email = ft.TextField(label="Email", value=self.user_data["email"])
            self.password = ft.TextField(
                label="New Password", password=True, can_reveal_password=True
            )

            self.controls = [
                ft.Row(
                    [
                        ft.IconButton(
                            icon=ft.icons.ARROW_BACK,
                            on_click=self.go_back,
                            tooltip="Back to Chats",
                        ),
                        ft.Container(
                            content=ft.Text(
                                "User Profile", style=ft.TextThemeStyle.HEADLINE_MEDIUM
                            ),
                            expand=True,
                            alignment=ft.alignment.center,
                        ),
                        ft.Container(
                            width=48
                        ),  # This container balances the width of the IconButton
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                self.username,
                self.email,
                self.password,
                ft.ElevatedButton("Save Changes", on_click=self.save_changes),
                ft.ElevatedButton("Logout", on_click=self.logout),
                ft.ElevatedButton(
                    "Delete Account",
                    on_click=self.delete_account,
                    color=ft.colors.RED_400,
                ),
            ]
            self.spacing = 20
            self.horizontal_alignment = ft.CrossAxisAlignment.CENTER
            self.expand = True
        else:
            self.logger.error(f"Failed to load user profile: {response.error}")
            self.chat_app.show_error_dialog("Error Loading Profile", response.error)
            self.controls = [ft.Text("Failed to load profile")]

    def go_back(self, e):
        """
        Navigates back to the chat list screen.
        """
        self.logger.info("Navigating back to chat list")
        self.chat_app.show_chat_list()

    def save_changes(self, e):
        """
        Saves the changes made to the user profile.
        """
        self.logger.info("Attempting to save profile changes")
        user_data = {
            "username": self.username.value,
            "email": self.email.value,
        }
        if self.password.value:
            user_data["password"] = self.password.value

        response = self.chat_app.api_client.update_user(user_data)
        if response.success:
            self.logger.info("Profile updated successfully")
            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Profile Updated"),
                content=ft.Text(
                    "Your profile has been updated successfully. You need to log in again for the changes to take effect."
                ),
                actions=[
                    ft.TextButton("Re-login", on_click=self.relogin),
                ],
                on_dismiss=self.relogin,
            )
            self.chat_app.page.open(dialog)
        else:
            self.logger.error(f"Failed to update profile: {response.error}")
            self.chat_app.show_error_dialog("Error Updating Profile", response.error)

    def relogin(self, e):
        """
        Handles the re-login process after profile update.
        """
        self.logger.info("Initiating re-login process")
        # Close any open dialogs
        self.chat_app.page.update()

        self.chat_app.api_client.token = None
        self.chat_app.show_login()

    def logout(self, e):
        """
        Handles the logout process and navigates directly to login.
        """
        self.logger.info("Attempting to log out")
        response = self.chat_app.api_client.logout()
        if response.success:
            self.logger.info("Logout successful")
            # Clear state and go directly to login
            self.chat_app.state_manager.logout_user()
            self.chat_app.show_login()
        else:
            self.logger.error(f"Failed to logout: {response.error}")
            self.chat_app.show_error_dialog("Error Logging Out", response.error)

    def delete_account(self, e):
        """
        Initiates the account deletion process.
        """
        self.logger.info("Initiating account deletion process")

        def confirm_delete(e):
            self.logger.info("Account deletion confirmed")
            response = self.chat_app.api_client.delete_user()
            if response.success:
                self.logger.info("Account deleted successfully")
                # Clear state and go directly to login
                self.chat_app.state_manager.logout_user()
                self.chat_app.show_login()
            else:
                self.logger.error(f"Failed to delete account: {response.error}")
                self.chat_app.show_error_dialog(
                    "Error Deleting Account", response.error
                )
            self.chat_app.page.close(dialog)

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Delete Account"),
            content=ft.Text(
                "Are you sure you want to delete your account? This action cannot be undone."
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: self.close_dialog(dialog)),
                ft.TextButton("Delete", on_click=confirm_delete),
            ],
            on_dismiss=lambda _: self.close_dialog(dialog),
        )
        self.chat_app.page.open(dialog)

    def close_dialog(self, dialog):
        """
        Closes the current dialog.
        """
        self.logger.info("Closing dialog")
        self.chat_app.page.close(dialog)

    def did_mount(self):
        """
        Called when the control is added to the page.
        """
        self.logger.info("UserProfileScreen mounted")

    def will_unmount(self):
        """
        Called when the control is about to be removed from the page.
        """
        self.logger.info("UserProfileScreen will unmount")
