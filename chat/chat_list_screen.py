import flet as ft

class ChatListScreen(ft.UserControl):
    def __init__(self, chat_app):
        super().__init__()
        self.chat_app = chat_app

    def build(self):
        self.search_input = ft.TextField(
            hint_text="Search users",
            expand=8,
        )
        self.search_button = ft.IconButton(
            icon=ft.icons.SEARCH,
            on_click=self.search_users,
            tooltip="Search",
        )
        self.search_results = ft.Dropdown(
            width=400,
            options=[],
            visible=False,
            on_change=self.start_chat_with_user
        )

        self.chat_list = ft.ListView(spacing=10, expand=True)

        return ft.Column(
            [
                ft.Row(
                    [
                        ft.IconButton(icon=ft.icons.PERSON, on_click=self.show_profile, tooltip="Profile"),
                        ft.Text("Chats", style=ft.TextThemeStyle.HEADLINE_MEDIUM),
                        ft.IconButton(icon=ft.icons.REFRESH, on_click=self.load_chats, tooltip="Refresh"),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                ),
                ft.Row([self.search_input, self.search_button]),
                self.search_results,
                self.chat_list,
            ],
            expand=True,
            spacing=20,
        )

    def load_chats(self, e=None):
        response = self.chat_app.api_client.get_chats()
        if response.success:
            self.chat_list.controls.clear()
            if not response.data:
                self.chat_list.controls.append(
                    ft.Text("No chats found. Search for users to start a new chat!",
                            style=ft.TextThemeStyle.BODY_LARGE,
                            color=ft.colors.GREY_500)
                )
            else:
                current_user_id = self.chat_app.api_client.get_current_user().data['id']
                for chat in response.data:
                    chat_name = ft.Text(chat['name'], style=ft.TextThemeStyle.TITLE_MEDIUM)

                    # Prepare the list of chat members
                    members = []
                    for member in chat['members']:
                        if member['id'] == current_user_id:
                            members.append("You")
                        else:
                            members.append(member['username'])
                    members_text = ft.Text(
                        ", ".join(members),
                        style=ft.TextThemeStyle.BODY_SMALL,
                        color=ft.colors.GREY_700
                    )

                    # Get unread messages count
                    unread_count_response = self.chat_app.api_client.get_unread_messages_count(chat['id'])
                    unread_count = unread_count_response.data if unread_count_response.success else 0

                    # Create unread messages indicator
                    unread_indicator = ft.Container(
                        content=ft.Text(str(unread_count), color=ft.colors.WHITE, size=12),
                        bgcolor=ft.colors.RED_500,
                        border_radius=ft.border_radius.all(10),
                        padding=ft.padding.all(5),
                        visible=unread_count > 0,
                        width=30,
                        height=30,
                        alignment=ft.alignment.center,
                    )

                    list_tile = ft.ListTile(
                        title=ft.Row(
                            [
                                ft.Column(
                                    [chat_name, members_text],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    spacing=5,
                                    expand=True
                                ),
                                unread_indicator,
                                ft.IconButton(
                                    icon=ft.icons.EDIT,
                                    on_click=lambda _, c=chat: self.edit_chat(c),
                                    tooltip="Edit chat"
                                ),
                                ft.IconButton(
                                    icon=ft.icons.DELETE,
                                    on_click=lambda _, c=chat: self.delete_chat(c),
                                    tooltip="Delete chat"
                                )
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        on_click=lambda _, chat_id=chat['id']: self.chat_app.show_chat(chat_id)
                    )
                    list_tile.data = chat  # Store the chat data in the ListTile
                    self.chat_list.controls.append(list_tile)
            self.update()
        else:
            self.chat_app.show_error_dialog("Error Loading Chats", f"Failed to load chats: {response.error}")


    def edit_chat(self, chat):
        def update_chat_name(e):
            if new_name.value:
                response = self.chat_app.api_client.update_chat(chat['id'], {"name": new_name.value})
                if response.success:
                    self.load_chats()
                    dialog.open = False
                    self.page.update()
                else:
                    self.chat_app.show_error_dialog("Error Updating Chat", f"Failed to update chat: {response.error}")
            else:
                self.chat_app.show_error_dialog("Invalid Input", "Please enter a chat name.")

        new_name = ft.TextField(value=chat['name'])
        dialog = ft.AlertDialog(
            title=ft.Text("Edit Chat Name"),
            content=new_name,
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: self.close_dialog(dialog)),
                ft.TextButton("Update", on_click=update_chat_name),
            ],
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def close_dialog(self, dialog):
        dialog.open = False
        self.page.update()

    def delete_chat(self, chat):
        def confirm_delete(e):
            response = self.chat_app.api_client.delete_chat(chat['id'])
            if response.success:
                # Remove the deleted chat from the chat list
                self.chat_list.controls = [c for c in self.chat_list.controls if
                                           isinstance(c, ft.ListTile) and c.data['id'] != chat['id']]
                if not self.chat_list.controls:
                    self.chat_list.controls.append(
                        ft.Text("No chats found. Search for users to start a new chat!",
                                style=ft.TextThemeStyle.BODY_LARGE,
                                color=ft.colors.GREY_500)
                    )
                self.update()  # Refresh the UI to reflect the changes
                dialog.open = False
                self.page.update()
            else:
                self.chat_app.show_error_dialog("Error Deleting Chat", f"Failed to delete chat: {response.error}")

        dialog = ft.AlertDialog(
            title=ft.Text("Delete Chat"),
            content=ft.Text(f"Are you sure you want to delete the chat '{chat['name']}'?"),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: self.close_dialog(dialog)),
                ft.TextButton("Delete", on_click=confirm_delete),
            ],
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def show_profile(self, e):
        self.chat_app.show_user_profile()

    def search_users(self, e):
        search_term = self.search_input.value
        if len(search_term) >= 1:
            response = self.chat_app.api_client.search_users(search_term)
            if response.success:
                self.search_results.options.clear()
                if response.data:
                    for user in response.data:
                        self.search_results.options.append(ft.dropdown.Option(key=str(user['id']), text=user['username']))
                else:
                    self.search_results.options.append(ft.dropdown.Option(key="no_results", text="No users found"))
                self.search_results.visible = True
                self.update()
            else:
                self.chat_app.show_error_dialog("Error Searching Users", f"Failed to search users: {response.error}")
        else:
            self.search_results.visible = False
            self.update()

    def start_chat_with_user(self, e):
        selected_user_id = self.search_results.value
        if selected_user_id and selected_user_id != "no_results":
            response = self.chat_app.api_client.start_chat(int(selected_user_id))
            if response.success:
                self.chat_app.show_chat(response.data['id'])
            else:
                self.chat_app.show_error_dialog("Error Starting Chat", f"Failed to start chat: {response.error}")
        self.search_input.value = ""
        self.search_results.value = None
        self.search_results.options.clear()
        self.search_results.visible = False
        self.chat_app.page.update()

    def did_mount(self):
        self.load_chats()