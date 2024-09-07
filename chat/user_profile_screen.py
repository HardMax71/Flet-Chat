import flet as ft


class UserProfileScreen(ft.UserControl):
    def __init__(self, chat_app):
        super().__init__()
        self.chat_app = chat_app

    def build(self):
        response = self.chat_app.api_client.get_current_user()
        if response.success:
            self.user_data = response.data
            self.username = ft.TextField(label="Username", value=self.user_data['username'])
            self.email = ft.TextField(label="Email", value=self.user_data['email'])
            self.password = ft.TextField(label="New Password", password=True, can_reveal_password=True)

            return ft.Column(
                [
                    ft.Row(
                        [
                            ft.IconButton(
                                icon=ft.icons.ARROW_BACK,
                                on_click=self.go_back,
                                tooltip="Back to Chats"
                            ),
                            ft.Container(
                                content=ft.Text("User Profile", style=ft.TextThemeStyle.HEADLINE_MEDIUM),
                                expand=True,
                                alignment=ft.alignment.center
                            ),
                            ft.Container(width=48),  # This container balances the width of the IconButton
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                    ),
                    self.username,
                    self.email,
                    self.password,
                    ft.ElevatedButton("Save Changes", on_click=self.save_changes),
                    ft.ElevatedButton("Logout", on_click=self.logout),
                    ft.ElevatedButton("Delete Account", on_click=self.delete_account, color=ft.colors.RED_400),
                ],
                spacing=20,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True,
            )
        else:
            self.chat_app.show_error_dialog("Error Loading Profile", f"Failed to load user profile: {response.error}")
            return ft.Text("Failed to load profile")

    def go_back(self, e):
        self.chat_app.show_chat_list()

    def save_changes(self, e):
        user_data = {
            "username": self.username.value,
            "email": self.email.value,
        }
        if self.password.value:
            user_data["password"] = self.password.value

        response = self.chat_app.api_client.update_user(user_data)
        if response.success:
            # Show a dialog with a button to log out and redirect to login
            dialog = ft.AlertDialog(
                title=ft.Text("Profile Updated"),
                content=ft.Text(
                    "Your profile has been updated successfully. You need to log in again for the changes to take effect."),
                actions=[
                    ft.TextButton("Re-login", on_click=self.relogin),
                ],
            )
            self.page.dialog = dialog
            dialog.open = True
            self.page.update()
        else:
            self.chat_app.show_error_dialog("Error Updating Profile", f"Failed to update profile: {response.error}")

    def relogin(self, e):
        # Close the dialog
        if self.page.dialog:
            self.page.dialog.open = False
            self.page.update()

        # Clear the token in the API client and show the login screen
        self.chat_app.api_client.token = None
        self.chat_app.show_login()

    def logout(self, e):
        # Clear the token in the API client
        self.chat_app.api_client.token = None
        self.chat_app.show_login()

    def delete_account(self, e):
        def confirm_delete(e):
            response = self.chat_app.api_client.delete_user()
            if response.success:
                self.chat_app.api_client.token = None
                self.chat_app.show_login()
            else:
                self.chat_app.show_error_dialog("Error Deleting Account", f"Failed to delete account: {response.error}")
            dialog.open = False
            self.page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Delete Account"),
            content=ft.Text("Are you sure you want to delete your account? This action cannot be undone."),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: self.close_dialog(dialog)),
                ft.TextButton("Delete", on_click=confirm_delete),
            ],
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def close_dialog(self, dialog):
        dialog.open = False
        self.page.update()
