import json
import logging
import threading
from datetime import datetime

import flet as ft


class ChatScreen(ft.Column):
    def __init__(self, chat_app, chat_id):
        super().__init__()
        self.chat_app = chat_app
        self.chat_id = chat_id
        self.current_user_id = None

        # We'll store the channel name and unsubscribe from it in will_unmount().
        self.chat_channel_name = f"chat:{self.chat_id}"

        # Configure logging
        self.logger = logging.getLogger('ChatScreen')
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s:%(name)s: %(message)s')
        handler.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(handler)

        # Initialize UI components
        self.chat_name = ft.Text("", style=ft.TextThemeStyle.HEADLINE_MEDIUM)
        self.message_list = ft.ListView(spacing=10, expand=True, auto_scroll=True)
        self.message_input = ft.TextField(
            hint_text="Type a message...",
            expand=True,
            multiline=True,
            min_lines=1,
            max_lines=5
        )

    def build(self):
        """
        The ChatScreen layout:
          - Top row with a back button, chat title, and more menu
          - self.message_list for chat messages
          - A row for the message input and 'Send' button
        """
        self.controls = [
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
                    ft.IconButton(
                        icon=ft.icons.SEND,
                        on_click=self.send_message
                    )
                ],
                spacing=10
            )
        ]
        self.expand = True
        self.spacing = 20

    def create_options_menu(self):
        """
        The triple-dot (MORE_VERT) popup menu for chat-level actions, e.g. Chat Info, Add/Remove member.
        """
        return ft.PopupMenuButton(
            icon=ft.icons.MORE_VERT,
            tooltip="Chat Options",
            items=[
                ft.PopupMenuItem(
                    text="Chat Info",
                    icon=ft.icons.INFO,
                    on_click=self.show_chat_info_dialog
                ),
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

    def show_chat_info_dialog(self, e):
        """
        Display a dialog with detailed information about the chat and its members.
        """
        def close_dialog(_e):
            self.chat_app.page.close(dialog)

        def format_member_info(member):
            """Format member information for display with proper truncation"""
            username = member['username']
            # Truncate long usernames
            if len(username) > 25:
                username = username[:25] + "..."
            
            if member['id'] == self.current_user_id:
                return f"You ({username})"
            else:
                return username

        # Get current chat data
        chat_data = getattr(self, 'current_chat_data', {})
        chat_name = chat_data.get('name', 'Unknown Chat')
        members = chat_data.get('members', [])
        
        # Truncate long chat name
        display_chat_name = chat_name
        if len(chat_name) > 40:
            display_chat_name = chat_name[:40] + "..."
        
        # Create chat info content
        chat_info_content = ft.Column([
            # Chat ID at top in italic
            ft.Container(
                content=ft.Text(f"Chat ID: {self.chat_id}", style=ft.TextThemeStyle.BODY_SMALL, italic=True, color=ft.colors.GREY_600),
                margin=ft.margin.only(bottom=10)
            ),
            
            # Chat name section
            ft.Container(
                content=ft.Text(display_chat_name, style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.BOLD),
                margin=ft.margin.only(bottom=20)
            ),
            
            # Members section
            ft.Container(
                content=ft.Column([
                    ft.Text(f"Members ({len(members)})", style=ft.TextThemeStyle.TITLE_SMALL, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    ft.Column([
                        ft.Container(
                            content=ft.Text(format_member_info(member), style=ft.TextThemeStyle.BODY_MEDIUM),
                            padding=ft.padding.symmetric(vertical=8, horizontal=12),
                            bgcolor=ft.colors.BLUE_50 if member['id'] == self.current_user_id else ft.colors.GREY_50,
                            border_radius=8,
                            margin=ft.margin.only(bottom=5)
                        )
                        for member in members
                    ], scroll=ft.ScrollMode.AUTO)
                ])
            )
        ], scroll=ft.ScrollMode.AUTO)

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Chat Information"),
            content=ft.Container(
                content=chat_info_content,
                width=400,
                height=500
            ),
            actions=[
                ft.TextButton("Close", on_click=close_dialog),
            ],
            on_dismiss=close_dialog,
        )

        self.chat_app.page.open(dialog)

    def show_add_member_dialog(self, e):
        """
        Display a dialog for searching and adding a member to the chat.
        """
        def close_dialog(_e):
            self.chat_app.page.close(dialog)

        def load_users_for_dialog():
            """Load all users for the combobox"""
            response = self.chat_app.api_client.search_users("")  # Empty search to get all users
            if response.success:
                user_combobox.options.clear()
                if response.data:
                    for user in response.data:
                        user_combobox.options.append(
                            ft.dropdown.Option(
                                key=str(user['id']),
                                text=user['username']
                            )
                        )
                else:
                    user_combobox.options.append(
                        ft.dropdown.Option(
                            key="no_users",
                            text="No users found"
                        )
                    )
                # Update the page instead of the specific control
                self.chat_app.page.update()
            else:
                self.chat_app.show_error_dialog("Error Loading Users", response.error)

        def add_member(_e):
            selected_user_id = user_combobox.value
            if selected_user_id and selected_user_id not in ["no_users", ""]:
                response = self.chat_app.api_client.add_chat_member(
                    self.chat_id,
                    int(selected_user_id)
                )
                if response.success:
                    self.load_chat()
                    self.chat_app.page.close(dialog)
                else:
                    self.chat_app.show_error_dialog("Error Adding Member", response.error)

        user_combobox = ft.Dropdown(
            hint_text="Search and select user to add",
            editable=True,
            enable_search=True,
            enable_filter=True,
            width=300,
            options=[],
            on_change=add_member,
        )

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Add Member"),
            content=user_combobox,
            actions=[
                ft.TextButton("Cancel", on_click=close_dialog),
            ],
            on_dismiss=close_dialog,
        )

        # Open dialog first, then load users
        self.chat_app.page.open(dialog)
        load_users_for_dialog()

    def show_remove_member_dialog(self, e):
        """
        Opens a dialog to remove a member from the chat.
        """
        def close_dialog(_e):
            self.chat_app.page.close(dialog)

        def remove_member(user_id):
            response = self.chat_app.api_client.remove_chat_member(self.chat_id, user_id)
            if response.success:
                self.load_chat()
                close_dialog(None)
            else:
                self.chat_app.show_error_dialog("Error Removing Member", response.error)

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
                modal=True,
                title=ft.Text("Remove Member"),
                content=member_list,
                actions=[
                    ft.TextButton("Close", on_click=close_dialog),
                ],
                on_dismiss=close_dialog,
            )

            self.chat_app.page.open(dialog)
        else:
            self.chat_app.show_error_dialog("Error Loading Members", response.error)

    def did_mount(self):
        """
        Called when the control is added to the page.
        Great place to load chat data and subscribe to channel.
        """
        self.logger.info(f"ChatScreen for chat ID {self.chat_id} mounted.")

        # Current user ID
        user_resp = self.chat_app.api_client.get_current_user()
        if user_resp.success and user_resp.data:
            self.current_user_id = user_resp.data['id']

        self.load_chat()

        # Ensure UI is rendered before loading messages
        self.update()

        # Load messages after UI is in place
        self.load_messages()

        # Subscribe to new messages for this chat
        self.chat_app.api_client.subscribe_to_channel(self.chat_channel_name, self.process_new_message)
        self.logger.info(f"Subscribed to channel {self.chat_channel_name} for new messages.")

    def will_unmount(self):
        """
        Called when the control is about to be removed from the page.
        """
        self.logger.info(f"ChatScreen for chat ID {self.chat_id} will unmount.")
        # Unsubscribe from this chat's channel
        self.chat_app.api_client.unsubscribe_from_channel(self.chat_channel_name)
        self.logger.info(f"Unsubscribed from channel {self.chat_channel_name}.")

    def process_new_message(self, data):
        """
        Processes new messages (or updates) received from Redis for this chat.
        """
        try:
            message = json.loads(data)
            self.logger.info(f"Received new message for chat ID {self.chat_id}: {message}")

            # Look for an existing row containing this message ID
            existing_message_row = next(
                (
                    row_control for row_control in self.message_list.controls
                    if isinstance(row_control, ft.Row)
                    and len(row_control.controls) > 0
                    and isinstance(row_control.controls[0], ft.GestureDetector)
                    and row_control.controls[0].content is not None
                    and isinstance(row_control.controls[0].content, ft.Container)
                    and row_control.controls[0].content.data == message['id']
                ),
                None
            )

            if existing_message_row:
                # Update existing message
                self.update_message_in_list(existing_message_row, message)
            else:
                # Add new message
                self.add_message_to_list(message)

            self.scroll_to_bottom()
            self.chat_app.page.update()

            # Mark the new message as read if it's not from the current user
            if message['user']['id'] != self.current_user_id:
                threading.Thread(
                    target=self.mark_message_as_read,
                    args=(message['id'],),
                    daemon=True
                ).start()

        except json.JSONDecodeError:
            self.logger.error(f"Failed to decode message: {data}")
        except Exception as e:
            self.logger.error(f"Error processing new message: {str(e)}")

    def update_message_in_list(self, existing_message_row, updated_message):
        """
        Updates an existing message in the message list (e.g. if edited or deleted).
        """
        # The first child of existing_message_row is a GestureDetector:
        gesture_detector = existing_message_row.controls[0]
        # Then its .content is the Container with `data=message_id` and a Column with 3 items
        #   [ Text(username), Text(content), Row([...time info...]) ]
        if not isinstance(gesture_detector, ft.GestureDetector):
            return

        message_container = gesture_detector.content
        if not isinstance(message_container, ft.Container) or not message_container.content:
            return

        column_content = message_container.content  # a ft.Column([...])
        if not isinstance(column_content, ft.Column) or len(column_content.controls) < 3:
            return

        # [ Text(username), Text(message_content), time_info_row ]
        # user_text = column_content.controls[0]   # ft.Text(username)
        message_text = column_content.controls[1]  # ft.Text(content or <deleted>)
        time_info = column_content.controls[2]     # ft.Row([... time info ...])

        is_current_user = updated_message['user']['id'] == self.current_user_id
        text_color = ft.colors.WHITE if is_current_user else ft.colors.BLACK

        if updated_message['is_deleted']:
            message_text.value = "<This message has been deleted>"
            message_text.color = ft.colors.GREY_400
        else:
            message_text.value = updated_message['content']
            message_text.color = text_color

        # Update the time info
        message_time = datetime.fromisoformat(updated_message['created_at'])
        formatted_time = message_time.strftime("%H:%M")
        if len(time_info.controls) > 0:
            time_info.controls[0].value = formatted_time

        # If message was edited
        if updated_message.get('updated_at') and updated_message['updated_at'] != updated_message['created_at']:
            edit_time = datetime.fromisoformat(updated_message['updated_at'])
            formatted_edit_time = edit_time.strftime("%H:%M")
            # Possibly the time_info row has a second text for "(edited ...)"
            if len(time_info.controls) > 1:
                time_info.controls[1].value = f"(edited at {formatted_edit_time})"
            else:
                time_info.controls.append(
                    ft.Text(
                        f"(edited at {formatted_edit_time})",
                        style=ft.TextThemeStyle.BODY_SMALL,
                        italic=True,
                        color=ft.colors.GREY_400 if is_current_user else ft.colors.GREY_700
                    )
                )

        self.logger.info(
            f"Updated message (ID: {updated_message['id']}) in the message list for chat ID {self.chat_id}"
        )

    def go_back(self, e):
        """
        Navigates back to the chat list screen.
        """
        self.logger.info(f"Navigating back to chat list from chat ID {self.chat_id}")
        self.chat_app.show_chat_list()

    def load_chat(self):
        """
        Loads chat details (like name) and updates `self.chat_name`.
        """
        self.logger.info(f"Loading chat details for chat ID {self.chat_id}")
        response = self.chat_app.api_client.get_chat(self.chat_id)
        if response.success:
            # Store chat data for use in info dialog
            self.current_chat_data = response.data
            self.chat_name.value = response.data['name']
            self.update()
            self.logger.info(f"Chat details loaded for chat ID {self.chat_id}")
        else:
            self.chat_app.show_error_dialog("Error Loading Chat", response.error)
            self.logger.error(f"Failed to load chat details for chat ID {self.chat_id}: {response.error}")

    def send_message(self, e):
        """
        Sends a new message via the API.
        """
        if self.message_input.value.strip():
            self.logger.info(f"Sending new message in chat ID {self.chat_id}")
            response = self.chat_app.api_client.send_message(self.chat_id, self.message_input.value.strip())
            if response.success:
                self.message_input.value = ""
                self.message_input.update()
                self.logger.info(f"Message sent in chat ID {self.chat_id}")
            else:
                self.chat_app.show_error_dialog("Error Sending Message", response.error)
                self.logger.error(f"Failed to send message in chat ID {self.chat_id}: {response.error}")

    def load_messages(self):
        """
        Loads messages from the server, populates self.message_list,
        and marks unread messages as read.
        """
        self.logger.info(f"Loading messages for chat ID {self.chat_id}")
        response = self.chat_app.api_client.get_messages(self.chat_id)
        if response.success:
            self.message_list.controls.clear()

            if not response.data:
                self.message_list.controls.append(
                    ft.Text(
                        "No messages yet. Start a conversation!",
                        style=ft.TextThemeStyle.BODY_LARGE,
                        color=ft.colors.GREY_500
                    )
                )
                self.logger.info(f"No messages found for chat ID {self.chat_id}")
            else:
                unread_message_ids = []
                # We reverse the list so older messages appear at the top
                for msg in reversed(response.data):
                    self.add_message_to_list(msg)
                    # Check if the message is unread by the current user
                    if (not msg['is_deleted']
                        and not any(st['is_read'] for st in msg['statuses']
                                    if st['user_id'] == self.current_user_id)):
                        unread_message_ids.append(msg['id'])

                self.logger.info(f"Loaded {len(response.data)} messages for chat {self.chat_id}")

                # Mark unread messages as read in background
                if unread_message_ids:
                    self.logger.info(
                        f"Marking {len(unread_message_ids)} messages as read for chat {self.chat_id}"
                    )
                    threading.Thread(
                        target=self.mark_messages_as_read,
                        args=(unread_message_ids,),
                        daemon=True
                    ).start()

            self.message_list.auto_scroll = True
            self.update()
        else:
            self.chat_app.show_error_dialog("Error Loading Messages", response.error)
            self.logger.error(f"Failed to load messages for chat {self.chat_id}: {response.error}")

    def add_message_to_list(self, message):
        """
        Creates a new Row+GestureDetector+Container with the message info and appends it
        to self.message_list.
        """
        # Remove "No messages yet" placeholder if it exists
        if (len(self.message_list.controls) == 1 
            and isinstance(self.message_list.controls[0], ft.Text) 
            and "No messages yet" in self.message_list.controls[0].value):
            self.message_list.controls.clear()
        
        is_current_user = (message['user']['id'] == self.current_user_id)
        message_color = ft.colors.BLUE_700 if is_current_user else ft.colors.GREY_200
        text_color = ft.colors.WHITE if is_current_user else ft.colors.BLACK
        alignment = ft.MainAxisAlignment.END if is_current_user else ft.MainAxisAlignment.START

        message_time = datetime.fromisoformat(message['created_at'])
        formatted_time = message_time.strftime("%H:%M")

        if message['is_deleted']:
            message_content = ft.Text(
                "<This message has been deleted>",
                style=ft.TextThemeStyle.BODY_MEDIUM,
                color=ft.colors.GREY_400
            )
        else:
            message_content = ft.Text(
                message['content'],
                style=ft.TextThemeStyle.BODY_MEDIUM,
                color=text_color
            )

        time_info = ft.Row(
            [
                ft.Text(
                    formatted_time,
                    style=ft.TextThemeStyle.BODY_SMALL,
                    color=ft.colors.GREY_400 if is_current_user else ft.colors.GREY_700
                )
            ],
            spacing=5
        )

        # If the message has been edited
        if message.get('updated_at') and message['updated_at'] != message['created_at']:
            edit_time = datetime.fromisoformat(message['updated_at'])
            formatted_edit_time = edit_time.strftime("%H:%M")
            time_info.controls.append(
                ft.Text(
                    f"(edited at {formatted_edit_time})",
                    style=ft.TextThemeStyle.BODY_SMALL,
                    italic=True,
                    color=ft.colors.GREY_400 if is_current_user else ft.colors.GREY_700
                )
            )

        # A Column with: [username, message_content, time_info]
        message_column = ft.Column([
            ft.Text(
                message['user']['username'],
                style=ft.TextThemeStyle.BODY_SMALL,
                color=text_color
            ),
            message_content,
            time_info
        ])

        # The Container storing message_column and `data=message['id']`
        message_container = ft.Container(
            content=message_column,
            bgcolor=message_color,
            border_radius=ft.border_radius.all(10),
            padding=10,
            width=300,
            data=message['id']  # Store message ID in container's data
        )

        # A GestureDetector to handle long-press events (for edit/delete, read info, etc.)
        gesture_detector = ft.GestureDetector(
            content=message_container,
            on_long_press_start=lambda e: self.show_message_options(e, message, is_current_user)
        )

        # Append a Row with the GestureDetector
        self.message_list.controls.append(
            ft.Row([gesture_detector], alignment=alignment)
        )
        self.logger.info(f"Added message (ID: {message['id']}) to the message list for chat ID {self.chat_id}")

    def scroll_to_bottom(self):
        """
        Scroll the ListView to the bottom (offset=-1) if there are any messages.
        """
        if len(self.message_list.controls) > 0:
            self.message_list.scroll_to(offset=-1, duration=300, curve=ft.AnimationCurve.EASE_OUT)

    def mark_message_as_read(self, message_id):
        """
        Mark a single message as read, calling the API. Runs in a background thread.
        """
        self.logger.info(f"Marking message ID {message_id} as read")
        response = self.chat_app.api_client.update_message_status(message_id, {"is_read": True})
        if not response.success:
            self.logger.error(f"Failed to mark message {message_id} as read: {response.error}")

    def mark_messages_as_read(self, message_ids):
        """
        Mark multiple messages as read in a loop.
        """
        self.logger.info(f"Marking {len(message_ids)} messages as read for chat {self.chat_id}")
        for mid in message_ids:
            self.mark_message_as_read(mid)

    def show_message_options(self, e, message, is_current_user):
        """
        Show a dialog with read status info, plus 'Edit' / 'Delete' if it's the user's own message.
        """
        # Refresh the message status before showing options
        msg_resp = self.chat_app.api_client.get_messages(
            self.chat_id, limit=1, content=message['content']
        )
        if msg_resp.success and msg_resp.data:
            updated_message = msg_resp.data[0]
        else:
            updated_message = message  # fallback if we can't fetch fresh data

        def close_dialog(_e):
            self.chat_app.page.close(options_dialog)

        # "Read by:" section
        read_status_title = ft.Text("Read by:", style=ft.TextThemeStyle.TITLE_SMALL, weight=ft.FontWeight.BOLD)
        read_status_list = ft.ListView(spacing=5, expand=True)

        # For each user status, find username and read time
        for status in updated_message['statuses']:
            # We need the username from the chat membership list
            chat_info = self.chat_app.api_client.get_chat(self.chat_id)
            if not chat_info.success:
                continue
            members = chat_info.data['members']
            reader_name = next(
                (m['username'] for m in members if m['id'] == status['user_id']),
                "Unknown"
            )

            if status['is_read']:
                read_time = None
                if status['read_at']:
                    read_time = datetime.fromisoformat(status['read_at'])
                formatted_time = read_time.strftime("%Y-%m-%d %H:%M:%S") if read_time else "Unknown"
                read_status_list.controls.append(
                    ft.Text(f"{reader_name}: {formatted_time}", style=ft.TextThemeStyle.BODY_SMALL)
                )
            else:
                read_status_list.controls.append(
                    ft.Text(f"{reader_name}: Unread", style=ft.TextThemeStyle.BODY_SMALL)
                )

        read_status_container = ft.Container(
            content=ft.Column(
                [
                    read_status_title,
                    read_status_list
                ],
                expand=True
            ),
            padding=10
        )

        options = [read_status_container]

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
            modal=True,
            title=ft.Text("Message Options", style=ft.TextThemeStyle.HEADLINE_SMALL),
            content=ft.Container(
                content=ft.Column(options, tight=True, scroll=ft.ScrollMode.AUTO),
                expand=True,
            ),
            actions=[
                ft.TextButton("Close", on_click=close_dialog),
            ],
            on_dismiss=close_dialog,
        )

        self.chat_app.page.open(options_dialog)

    def edit_message(self, message):
        """
        Prompts the user to edit this message's content.
        """
        def update_message_content(_e):
            if new_content.value.strip():
                resp = self.chat_app.api_client.update_message(
                    message['id'], {"content": new_content.value.strip()}
                )
                if resp.success:
                    self.load_messages()
                    self.chat_app.page.close(dialog)
                else:
                    self.chat_app.show_error_dialog("Error Updating Message", resp.error)
            else:
                self.chat_app.show_error_dialog("Invalid Input", {"detail": "Please enter message content."})

        new_content = ft.TextField(value=message['content'], multiline=True)
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Edit Message"),
            content=new_content,
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: self.close_dialog(dialog)),
                ft.TextButton("Update", on_click=update_message_content),
            ],
            on_dismiss=lambda _: self.close_dialog(dialog),
        )
        self.chat_app.page.open(dialog)

    def delete_message(self, message):
        """
        Prompts the user to confirm deletion, then calls API to delete the message.
        """
        def confirm_delete(_e):
            resp = self.chat_app.api_client.delete_message(message['id'])
            if resp.success:
                self.load_messages()
                self.chat_app.page.close(dialog)
            else:
                self.chat_app.show_error_dialog("Error Deleting Message", resp.error)

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Delete Message"),
            content=ft.Text("Are you sure you want to delete this message?"),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: self.close_dialog(dialog)),
                ft.TextButton("Delete", on_click=confirm_delete),
            ],
            on_dismiss=lambda _: self.close_dialog(dialog),
        )
        self.chat_app.page.open(dialog)

    def close_dialog(self, dialog):
        """
        Closes an AlertDialog and clears the page.dialog reference.
        """
        self.chat_app.page.close(dialog)
