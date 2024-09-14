import json
import logging
import threading
from datetime import datetime

import flet as ft

class ChatScreen(ft.UserControl):
    def __init__(self, chat_app, chat_id):
        super().__init__()
        self.chat_app = chat_app
        self.chat_id = chat_id
        self.current_user_id = None
        self.chat_subscription = None

        # Configure logging
        self.logger = logging.getLogger('ChatScreen')
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s:%(name)s: %(message)s')
        handler.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(handler)

    def build(self):
        self.chat_name = ft.Text("", style=ft.TextThemeStyle.HEADLINE_MEDIUM)
        self.message_list = ft.ListView(spacing=10, expand=True, auto_scroll=True)
        self.message_input = ft.TextField(hint_text="Type a message...",
                                          expand=True,
                                          multiline=True,
                                          min_lines=1, max_lines=5)

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
                            content=self.chat_name,
                            expand=True,
                            alignment=ft.alignment.center
                        ),
                        self.create_options_menu(),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                ),
                self.message_list,
                ft.Row(
                    [
                        self.message_input,
                        ft.IconButton(icon=ft.icons.SEND, on_click=self.send_message)
                    ],
                    spacing=10
                )
            ],
            expand=True,
            spacing=20,
        )

    def create_options_menu(self):
        return ft.PopupMenuButton(
            icon=ft.icons.MORE_VERT,
            tooltip="Chat Options",
            items=[
                ft.PopupMenuItem(
                    text="Add Member",
                    icon=ft.icons.PERSON_ADD,
                    on_click=self.show_add_member_dialog
                ),
                ft.PopupMenuItem(
                    text="Remove Member",
                    icon=ft.icons.PERSON_REMOVE,
                    on_click=self.show_remove_member_dialog
                ),
            ],
        )

    def show_add_member_dialog(self, e):
        def close_dialog(e):
            dialog.open = False
            self.page.update()

        def search_users(e):
            search_term = search_field.value
            if len(search_term) >= 1:
                response = self.chat_app.api_client.search_users(search_term)
                if response.success:
                    search_results.options.clear()
                    if response.data:
                        for user in response.data:
                            search_results.options.append(
                                ft.dropdown.Option(key=str(user['id']), text=user['username']))
                    else:
                        search_results.options.append(ft.dropdown.Option(key="no_results", text="No users found"))
                    search_results.visible = True
                else:
                    self.chat_app.show_error_dialog("Error Searching Users",
                                                    f"Failed to search users: {response.error}")
            else:
                search_results.visible = False
            dialog.update()

        def add_member(e):
            selected_user_id = search_results.value
            if selected_user_id and selected_user_id != "no_results":
                response = self.chat_app.api_client.add_chat_member(self.chat_id, int(selected_user_id))
                if response.success:
                    self.load_chat()
                    dialog.open = False
                    self.page.update()
                else:
                    self.chat_app.show_error_dialog("Error Adding Member", f"Failed to add member: {response.error}")

        search_field = ft.TextField(
            hint_text="Search users",
            expand=True,
            on_submit=search_users
        )
        search_button = ft.IconButton(
            icon=ft.icons.SEARCH,
            on_click=search_users,
            tooltip="Search",
        )
        search_results = ft.Dropdown(
            options=[],
            visible=False,
        )

        dialog = ft.AlertDialog(
            title=ft.Text("Add Member"),
            content=ft.Column([
                ft.Row([search_field, search_button]),
                search_results,
            ]),
            actions=[
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.TextButton("Add", on_click=add_member),
            ],
        )

        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def show_remove_member_dialog(self, e):
        def close_dialog(e):
            dialog.open = False
            self.page.update()

        def remove_member(user_id):
            response = self.chat_app.api_client.remove_chat_member(self.chat_id, user_id)
            if response.success:
                self.load_chat()
                close_dialog(None)
            else:
                self.chat_app.show_error_dialog("Error Removing Member", f"Failed to remove member: {response.error}")

        response = self.chat_app.api_client.get_chat(self.chat_id)
        if response.success:
            members = response.data['members']
            member_list = ft.Column([
                ft.Row([
                    ft.Text(member['username'], expand=True),
                    ft.IconButton(
                        icon=ft.icons.REMOVE,
                        on_click=lambda _, m=member: remove_member(m['id']),
                        tooltip="Remove"
                    ) if member['id'] != self.current_user_id else ft.Container()
                ])
                for member in members
            ])

            dialog = ft.AlertDialog(
                title=ft.Text("Remove Member"),
                content=member_list,
                actions=[
                    ft.TextButton("Close", on_click=close_dialog),
                ],
            )

            self.page.dialog = dialog
            dialog.open = True
            self.page.update()
        else:
            self.chat_app.show_error_dialog("Error Loading Members", f"Failed to load chat members: {response.error}")

    def did_mount(self):
        """
        Called when the control is added to the page. Initializes the chat screen.
        """
        self.logger.info(f"ChatScreen for chat ID {self.chat_id} mounted.")
        self.current_user_id = self.chat_app.api_client.get_current_user().data['id']
        self.load_chat()
        self.load_messages()
        # Subscribe to new messages
        channel_name = f"chat:{self.chat_id}"
        self.chat_subscription = self.chat_app.api_client.subscribe_to_channel(channel_name, self.process_new_message)
        self.logger.info(f"Subscribed to channel {channel_name} for new messages.")

    def will_unmount(self):
        """
        Called when the control is about to be removed from the page. Cleans up subscriptions.
        """
        self.logger.info(f"ChatScreen for chat ID {self.chat_id} will unmount.")
        # Unsubscribe from the Redis channel
        if self.chat_subscription:
            self.chat_app.api_client.unsubscribe_from_channel(self.chat_subscription)
            self.logger.info(f"Unsubscribed from channel {self.chat_subscription}.")

    def process_new_message(self, data):
        """
        Processes new messages received from Redis.
        """
        try:
            message = json.loads(data)
            self.logger.info(f"Received new message for chat ID {self.chat_id}: {message}")
            if message['user']['id'] != self.current_user_id:
                self.add_message_to_list(message)
                self.update()
                # Mark the new message as read
                threading.Thread(target=self.mark_message_as_read, args=(message['id'],), daemon=True).start()
        except json.JSONDecodeError:
            self.logger.error(f"Failed to decode message: {data}")
        except Exception as e:
            self.logger.error(f"Error processing new message: {str(e)}")


    def go_back(self, e):
        """
        Navigates back to the chat list screen.
        """
        self.logger.info(f"Navigating back to chat list from chat ID {self.chat_id}")
        self.chat_app.show_chat_list()

    def load_chat(self):
        """
        Loads chat details and updates the chat name.
        """
        self.logger.info(f"Loading chat details for chat ID {self.chat_id}")
        response = self.chat_app.api_client.get_chat(self.chat_id)
        if response.success:
            self.chat_name.value = response.data['name']
            self.update()
            self.logger.info(f"Chat details loaded successfully for chat ID {self.chat_id}")
        else:
            self.chat_app.show_error_dialog("Error Loading Chat", f"Failed to load chat: {response.error}")
            self.logger.error(f"Failed to load chat details for chat ID {self.chat_id}: {response.error}")

    def send_message(self, e):
        """
        Sends a new message and adds it to the message list.
        """
        if self.message_input.value:
            self.logger.info(f"Sending new message in chat ID {self.chat_id}")
            response = self.chat_app.api_client.send_message(self.chat_id, self.message_input.value)
            if response.success:
                self.message_input.value = ""
                self.add_message_to_list(response.data)
                self.update()
                self.logger.info(f"Message sent successfully in chat ID {self.chat_id}")
            else:
                self.chat_app.show_error_dialog("Error Sending Message", f"Failed to send message: {response.error}")
                self.logger.error(f"Failed to send message in chat ID {self.chat_id}: {response.error}")

    def load_messages(self):
        """
        Loads messages for the chat and marks unread messages as read.
        """
        self.logger.info(f"Loading messages for chat ID {self.chat_id}")
        response = self.chat_app.api_client.get_messages(self.chat_id)
        if response.success:
            self.message_list.controls.clear()
            if not response.data:
                self.message_list.controls.append(
                    ft.Text("No messages yet. Start a conversation!",
                            style=ft.TextThemeStyle.BODY_LARGE,
                            color=ft.colors.GREY_500)
                )
                self.logger.info(f"No messages found for chat ID {self.chat_id}")
            else:
                unread_message_ids = []
                for message in reversed(response.data):
                    self.add_message_to_list(message)
                    # Check if the message is unread by the current user
                    if not message['is_deleted'] and not any(status['is_read'] for status in message['statuses'] if
                                                             status['user_id'] == self.current_user_id):
                        unread_message_ids.append(message['id'])

                self.logger.info(f"Loaded {len(response.data)} messages for chat ID {self.chat_id}")

                # Mark unread messages as read
                if unread_message_ids:
                    self.logger.info(f"Marking {len(unread_message_ids)} messages as read for chat ID {self.chat_id}")
                    threading.Thread(target=self.mark_messages_as_read, args=(unread_message_ids,), daemon=True).start()

            self.message_list.auto_scroll = True
            self.update()
        else:
            self.chat_app.show_error_dialog("Error Loading Messages", f"Failed to load messages: {response.error}")
            self.logger.error(f"Failed to load messages for chat ID {self.chat_id}: {response.error}")

    def add_message_to_list(self, message):
        """
        Adds a single message to the message list UI.
        """
        is_current_user = message['user']['id'] == self.current_user_id
        message_color = ft.colors.BLUE_700 if is_current_user else ft.colors.GREY_200
        text_color = ft.colors.WHITE if is_current_user else ft.colors.BLACK
        alignment = ft.MainAxisAlignment.END if is_current_user else ft.MainAxisAlignment.START

        message_time = datetime.fromisoformat(message['created_at'])
        formatted_time = message_time.strftime("%H:%M")

        if message['is_deleted']:
            message_content = ft.Text("<This message has been deleted>",
                                      style=ft.TextThemeStyle.BODY_MEDIUM,
                                      color=ft.colors.GREY_400)
        else:
            message_content = ft.Text(message['content'],
                                      style=ft.TextThemeStyle.BODY_MEDIUM,
                                      color=text_color)

        time_info = ft.Row(
            [
                ft.Text(formatted_time,
                        style=ft.TextThemeStyle.BODY_SMALL,
                        color=ft.colors.GREY_400 if is_current_user else ft.colors.GREY_700)
            ],
            spacing=5
        )

        if message.get('updated_at') and message['updated_at'] != message['created_at']:
            edit_time = datetime.fromisoformat(message['updated_at'])
            formatted_edit_time = edit_time.strftime("%H:%M")
            time_info.controls.append(
                ft.Text(f"(edited at {formatted_edit_time})",
                        style=ft.TextThemeStyle.BODY_SMALL,
                        italic=True,
                        color=ft.colors.GREY_400 if is_current_user else ft.colors.GREY_700)
            )

        message_container = ft.GestureDetector(
            content=ft.Container(
                content=ft.Column([
                    ft.Text(message['user']['username'],
                            style=ft.TextThemeStyle.BODY_SMALL,
                            color=text_color),
                    message_content,
                    time_info
                ]),
                bgcolor=message_color,
                border_radius=ft.border_radius.all(10),
                padding=10,
                width=300,
            ),
            on_long_press_start=lambda e: self.show_message_options(e, message, is_current_user),
        )

        self.message_list.controls.append(
            ft.Row([message_container], alignment=alignment)
        )

        self.logger.info(f"Added message (ID: {message['id']}) to the message list for chat ID {self.chat_id}")

    def mark_message_as_read(self, message_id):
        """
        Marks a single message as read.
        """
        self.logger.info(f"Marking message ID {message_id} as read")
        response = self.chat_app.api_client.update_message_status(message_id, {"is_read": True})
        if not response.success:
            self.logger.error(f"Failed to mark message {message_id} as read: {response.error}")

    def mark_messages_as_read(self, message_ids):
        """
        Marks multiple messages as read.
        """
        self.logger.info(f"Marking {len(message_ids)} messages as read")
        for message_id in message_ids:
            self.mark_message_as_read(message_id)

    def show_message_options(self, e, message, is_current_user):
        # Refresh the message status before showing options
        updated_message = (self.chat_app
        .api_client
        .get_messages(self.chat_id,
                      limit=1,
                      content=message['content']).data[0])

        def close_dialog(e):
            options_dialog.open = False
            self.page.dialog = None
            self.page.update()

        options = []

        # Add read status information
        read_status_title = ft.Text("Read by:", style=ft.TextThemeStyle.TITLE_SMALL, weight=ft.FontWeight.BOLD)

        read_status_list = ft.ListView(
            spacing=5,
            expand=True,
        )

        for status in updated_message['statuses']:
            if status['is_read']:
                read_time = datetime.fromisoformat(status['read_at']) if status['read_at'] else None
                formatted_time = read_time.strftime("%Y-%m-%d %H:%M:%S") if read_time else "Unknown"
                reader_name = next(
                    (member['username'] for member in self.chat_app.api_client.get_chat(self.chat_id).data['members'] if
                     member['id'] == status['user_id']), "Unknown")
                read_status_list.controls.append(
                    ft.Text(f"{reader_name}: {formatted_time}", style=ft.TextThemeStyle.BODY_SMALL)
                )

        if not any(status['is_read'] for status in updated_message['statuses']):
            read_status_list.controls.append(
                ft.Text("No one has read this message yet.", style=ft.TextThemeStyle.BODY_SMALL)
            )

        read_status_container = ft.Container(
            content=ft.Column([
                read_status_title,
                read_status_list
            ],
                expand=True),
            padding=10
        )

        options.append(read_status_container)

        if is_current_user and not message['is_deleted']:
            options.extend([
                ft.Divider(),
                ft.ListTile(
                    leading=ft.Icon(ft.icons.EDIT),
                    title=ft.Text("Edit", style=ft.TextThemeStyle.TITLE_MEDIUM),
                    subtitle=ft.Text("Modify your message", style=ft.TextThemeStyle.BODY_SMALL),
                    on_click=lambda _: self.edit_message(message)
                ),
                ft.ListTile(
                    leading=ft.Icon(ft.icons.DELETE),
                    title=ft.Text("Delete", style=ft.TextThemeStyle.TITLE_MEDIUM),
                    subtitle=ft.Text("Remove this message", style=ft.TextThemeStyle.BODY_SMALL),
                    on_click=lambda _: self.delete_message(message)
                ),
            ])

        options_dialog = ft.AlertDialog(
            title=ft.Text("Message Options", style=ft.TextThemeStyle.HEADLINE_SMALL),
            content=ft.Container(
                content=ft.Column(options, tight=True, scroll=ft.ScrollMode.AUTO),
                expand=True,
            ),
            actions=[
                ft.TextButton("Close", on_click=close_dialog),
            ],
        )

        self.page.dialog = options_dialog
        options_dialog.open = True
        self.page.update()

    def edit_message(self, message):
        def update_message_content(e):
            if new_content.value:
                response = self.chat_app.api_client.update_message(message['id'], {"content": new_content.value})
                if response.success:
                    self.load_messages()
                    dialog.open = False
                    self.page.update()
                else:
                    self.chat_app.show_error_dialog("Error Updating Message",
                                                    f"Failed to update message: {response.error}")
            else:
                self.chat_app.show_error_dialog("Invalid Input", "Please enter a message content.")

        new_content = ft.TextField(value=message['content'], multiline=True)
        dialog = ft.AlertDialog(
            title=ft.Text("Edit Message"),
            content=new_content,
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: self.close_dialog(dialog)),
                ft.TextButton("Update", on_click=update_message_content),
            ],
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def delete_message(self, message):
        def confirm_delete(e):
            response = self.chat_app.api_client.delete_message(message['id'])
            if response.success:
                self.load_messages()
                dialog.open = False
                self.page.update()
            else:
                self.chat_app.show_error_dialog("Error Deleting Message", f"Failed to delete message: {response.error}")

        dialog = ft.AlertDialog(
            title=ft.Text("Delete Message"),
            content=ft.Text("Are you sure you want to delete this message?"),
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
        self.page.dialog = None
        self.page.update()
