import json
import logging

import flet as ft


class ChatListScreen(ft.Column):
    def __init__(self, chat_app):
        super().__init__()
        self.isolated = True
        self.chat_app = chat_app
        self.chat_subscriptions = {}  # Keep track of subscribed chats
        self.current_user_id = None

        # Configure logging
        self.logger = logging.getLogger('ChatListScreen')
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s:%(name)s: %(message)s')
        handler.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(handler)

        # GUI elements
        self.loading_indicator = ft.ProgressRing(visible=False)
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
        self.loading_container = ft.Container(
            content=ft.Column(
                [
                    ft.ProgressRing(),
                    ft.Text("Chats are being loaded...", style=ft.TextThemeStyle.BODY_MEDIUM)
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10
            ),
            alignment=ft.alignment.center,
            expand=True,
            visible=False
        )

    def build(self):
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
                ft.Stack(
                    [
                        self.chat_list,
                        self.loading_container
                    ],
                    expand=True
                )
            ],
            expand=True,
            spacing=20,
        )

    def load_chats(self, e=None):
        self.loading_container.visible = True
        self.chat_list.visible = False
        self.update()

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
                current_user_response = self.chat_app.api_client.get_current_user()
                if current_user_response.success:
                    self.current_user_id = current_user_response.data['id']
                else:
                    self.chat_app.show_error_dialog("Error", "Failed to get current user.")
                    self.loading_indicator.visible = False
                    self.update()
                    return

                for chat in response.data:
                    chat_name = ft.Text(chat['name'], style=ft.TextThemeStyle.TITLE_MEDIUM)

                    # Prepare the list of chat members
                    members = []
                    for member in chat['members']:
                        if member['id'] == self.current_user_id:
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
                    list_tile.controls_dict = {'unread_indicator': unread_indicator}
                    self.chat_list.controls.append(list_tile)

                    # Subscribe to unread count updates via Redis
                    self.subscribe_to_unread_count(chat['id'])

            self.logger.info("Chats loaded successfully.")
        else:
            self.chat_app.show_error_dialog("Error Loading Chats", f"Failed to load chats: {response.error}")
            self.logger.error(f"Failed to load chats: {response.error}")

        self.loading_container.visible = False
        self.chat_list.visible = True
        self.update()

    def subscribe_to_unread_count(self, chat_id):
        channel_name = f"chat:{chat_id}:unread_count:{self.current_user_id}"
        if channel_name not in self.chat_subscriptions:
            self.chat_subscriptions[channel_name] = chat_id
            self.chat_app.api_client.subscribe_to_channel(channel_name, self.update_unread_count)
            self.logger.info(f"Subscribed to unread count channel '{channel_name}' for chat ID {chat_id}")

    def unsubscribe_from_unread_count(self, chat_id):
        channel_name = f"chat:{chat_id}:unread_count:{self.current_user_id}"
        if channel_name in self.chat_subscriptions:
            self.chat_app.api_client.unsubscribe_from_channel(channel_name)
            del self.chat_subscriptions[channel_name]
            self.logger.info(f"Unsubscribed from unread count channel '{channel_name}' for chat ID {chat_id}")

    def update_unread_count(self, data):
        """
        Callback function to handle unread count updates from Redis.
        """
        try:
            message = json.loads(data)
            chat_id = message['chat_id']
            unread_count = message['unread_count']
            user_id = message['user_id']

            if user_id != self.current_user_id:
                return  # Ignore updates for other users

            self.logger.info(f"Received unread count update for chat ID {chat_id}: {unread_count}")

            self.load_chats()  # Reload the chat list to update the unread count

            self.page.update()
            self.logger.info(f"Updated UI for unread count on chat ID {chat_id}")
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to decode unread count message: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error processing unread count update: {str(e)}")

    def edit_chat(self, chat):
        def update_chat_name(e):
            if new_name.value:
                response = self.chat_app.api_client.update_chat(chat['id'], {"name": new_name.value})
                if response.success:
                    self.load_chats()
                    dialog.open = False
                    self.page.update()
                    self.logger.info(f"Chat ID {chat['id']} renamed to '{new_name.value}'")
                else:
                    self.chat_app.show_error_dialog("Error Updating Chat", f"Failed to update chat: {response.error}")
                    self.logger.error(f"Failed to update chat ID {chat['id']}: {response.error}")
            else:
                self.chat_app.show_error_dialog("Invalid Input", "Please enter a chat name.")
                self.logger.warning("Attempted to update chat without providing a new name.")

        new_name = ft.TextField(value=chat['name'], label="Chat Name")
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
        self.logger.info(f"Opened edit chat dialog for chat ID {chat['id']}")

    def close_dialog(self, dialog):
        """
        Closes the specified dialog.
        """
        dialog.open = False
        self.page.dialog = None
        self.page.update()
        self.logger.info("Closed dialog.")

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
                self.logger.info(f"Deleted chat ID {chat['id']} successfully.")
            else:
                self.chat_app.show_error_dialog("Error Deleting Chat", f"Failed to delete chat: {response.error}")
                self.logger.error(f"Failed to delete chat ID {chat['id']}: {response.error}")

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
        self.logger.info(f"Opened delete chat dialog for chat ID {chat['id']}")

    def show_profile(self, e):
        self.chat_app.show_user_profile()
        self.logger.info("Navigated to user profile.")

    def search_users(self, e):
        search_term = self.search_input.value.strip()
        if len(search_term) >= 1:
            self.logger.info(f"Searching users with term: '{search_term}'")
            response = self.chat_app.api_client.search_users(search_term)
            if response.success:
                self.search_results.options.clear()
                if response.data:
                    for user in response.data:
                        self.search_results.options.append(
                            ft.dropdown.Option(key=str(user['id']), text=user['username']))
                    self.logger.info(f"Found {len(response.data)} users matching '{search_term}'.")
                else:
                    self.search_results.options.append(ft.dropdown.Option(key="no_results", text="No users found"))
                    self.logger.info(f"No users found matching '{search_term}'.")
                self.search_results.visible = True
            else:
                self.chat_app.show_error_dialog("Error Searching Users", f"Failed to search users: {response.error}")
                self.logger.error(f"Failed to search users: {response.error}")
        else:
            self.search_results.visible = False
            self.logger.info("Search term is too short. Hiding search results.")

        self.update()

    def start_chat_with_user(self, e):
        selected_user_id = self.search_results.value
        if selected_user_id and selected_user_id != "no_results":
            self.logger.info(f"Starting chat with user ID {selected_user_id}")
            response = self.chat_app.api_client.start_chat(int(selected_user_id))
            if response.success:
                self.chat_app.show_chat(response.data['id'])
                self.logger.info(f"Chat started with user ID {selected_user_id}")
            else:
                self.chat_app.show_error_dialog("Error Starting Chat", f"Failed to start chat: {response.error}")
                self.logger.error(f"Failed to start chat with user ID {selected_user_id}: {response.error}")

        # Reset search fields
        self.search_input.value = ""
        self.search_results.value = None
        self.search_results.options.clear()
        self.search_results.visible = False
        self.update()
        self.logger.info("Reset search input and results after attempting to start chat.")

    def did_mount(self):
        """
        Called when the control is mounted. Loads chats and subscribes to updates.
        """
        self.logger.info("ChatListScreen mounted. Loading chats...")
        self.load_chats()

    def will_unmount(self):
        """
        Called when the control is about to be unmounted. Unsubscribes from all channels.
        """
        self.logger.info("ChatListScreen will unmount. Unsubscribing from all channels...")
        for channel_name in list(self.chat_subscriptions.keys()):
            chat_id = self.chat_subscriptions[channel_name]
            self.unsubscribe_from_unread_count(chat_id)
