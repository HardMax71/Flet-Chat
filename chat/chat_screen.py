import json
import logging
import threading
from datetime import datetime

import flet as ft

from .state_manager import AppState, StateEvent


class ChatScreen(ft.Column):
    def __init__(self, chat_app, chat_id):
        super().__init__()
        self.chat_app = chat_app
        self.chat_id = chat_id
        self.current_user_id = None
        self.app_state = AppState()

        # We'll store the channel name and unsubscribe from it in will_unmount().
        self.chat_channel_name = f"chat:{self.chat_id}"

        # Configure logging
        self.logger = logging.getLogger("ChatScreen")
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s:%(name)s: %(message)s"
        )
        handler.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(handler)

        # Initialize UI components
        self.chat_name = ft.Text("", style=ft.TextThemeStyle.HEADLINE_MEDIUM)
        self.message_list = ft.ListView(
            spacing=10,
            expand=True,
            auto_scroll=False,  # Disable auto_scroll to control manually
            on_scroll=self._on_scroll_change,
        )
        self.message_input = ft.TextField(
            hint_text="Type a message...",
            expand=True,
            multiline=True,
            min_lines=1,
            max_lines=5,
            on_submit=self.send_message,
        )

        # Track scroll state to prevent unwanted auto-scrolling
        self.user_is_at_bottom = True
        self.first_unread_message_index = None

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
                        tooltip="Back to Chats",
                    ),
                    ft.Container(
                        content=self.chat_name,
                        expand=True,
                        alignment=ft.alignment.center,
                    ),
                    self.create_options_menu(),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            self.message_list,
            ft.Row(
                [
                    self.message_input,
                    ft.IconButton(icon=ft.icons.SEND, on_click=self.send_message),
                ],
                spacing=10,
            ),
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
                    on_click=self.show_chat_info_dialog,
                ),
                ft.PopupMenuItem(
                    text="Add Member",
                    icon=ft.icons.PERSON_ADD,
                    on_click=self.show_add_member_dialog,
                ),
                ft.PopupMenuItem(
                    text="Remove Member",
                    icon=ft.icons.PERSON_REMOVE,
                    on_click=self.show_remove_member_dialog,
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
            username = member["username"]
            # Truncate long usernames
            if len(username) > 25:
                username = username[:25] + "..."

            if member["id"] == self.current_user_id:
                return f"You ({username})"
            else:
                return username

        # Get current chat data
        chat_data = getattr(self, "current_chat_data", {})
        chat_name = chat_data.get("name", "Unknown Chat")
        members = chat_data.get("members", [])

        # Truncate long chat name
        display_chat_name = chat_name
        if len(chat_name) > 40:
            display_chat_name = chat_name[:40] + "..."

        # Create chat info content
        chat_info_content = ft.Column(
            [
                # Chat ID at top in italic
                ft.Container(
                    content=ft.Text(
                        f"Chat ID: {self.chat_id}",
                        style=ft.TextThemeStyle.BODY_SMALL,
                        italic=True,
                        color=ft.colors.GREY_600,
                    ),
                    margin=ft.margin.only(bottom=10),
                ),
                # Chat name section
                ft.Container(
                    content=ft.Text(
                        display_chat_name,
                        style=ft.TextThemeStyle.TITLE_MEDIUM,
                        weight=ft.FontWeight.BOLD,
                    ),
                    margin=ft.margin.only(bottom=20),
                ),
                # Members section
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                f"Members ({len(members)})",
                                style=ft.TextThemeStyle.TITLE_SMALL,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Divider(),
                            ft.Column(
                                [
                                    ft.Container(
                                        content=ft.Text(
                                            format_member_info(member),
                                            style=ft.TextThemeStyle.BODY_MEDIUM,
                                        ),
                                        padding=ft.padding.symmetric(
                                            vertical=8, horizontal=12
                                        ),
                                        bgcolor=ft.colors.BLUE_50
                                        if member["id"] == self.current_user_id
                                        else ft.colors.GREY_50,
                                        border_radius=8,
                                        margin=ft.margin.only(bottom=5),
                                    )
                                    for member in members
                                ],
                                scroll=ft.ScrollMode.AUTO,
                            ),
                        ]
                    )
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
        )

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Chat Information"),
            content=ft.Container(content=chat_info_content, width=400, height=500),
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
            response = self.chat_app.api_client.search_users(
                ""
            )  # Empty search to get all users
            if response.success:
                user_combobox.options.clear()
                if response.data:
                    for user in response.data:
                        user_combobox.options.append(
                            ft.dropdown.Option(
                                key=str(user["id"]), text=user["username"]
                            )
                        )
                else:
                    user_combobox.options.append(
                        ft.dropdown.Option(key="no_users", text="No users found")
                    )
                # Update the page instead of the specific control
                self.chat_app.page.update()
            else:
                self.chat_app.show_error_dialog("Error Loading Users", response.error)

        def add_member(_e):
            selected_user_id = user_combobox.value
            if selected_user_id and selected_user_id not in ["no_users", ""]:
                response = self.chat_app.api_client.add_chat_member(
                    self.chat_id, int(selected_user_id)
                )
                if response.success:
                    self.load_chat()
                    self.chat_app.page.close(dialog)
                else:
                    self.chat_app.show_error_dialog(
                        "Error Adding Member", response.error
                    )

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
            response = self.chat_app.api_client.remove_chat_member(
                self.chat_id, user_id
            )
            if response.success:
                self.load_chat()
                close_dialog(None)
            else:
                self.chat_app.show_error_dialog("Error Removing Member", response.error)

        response = self.chat_app.api_client.get_chat(self.chat_id)
        if response.success:
            members = response.data["members"]
            member_list = ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(member["username"], expand=True),
                            ft.IconButton(
                                icon=ft.icons.REMOVE,
                                on_click=lambda _, m=member: remove_member(m["id"]),
                                tooltip="Remove",
                            )
                            if member["id"] != self.current_user_id
                            else ft.Container(),
                        ]
                    )
                    for member in members
                ]
            )

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

        # Get current user from state (should be available via state manager)
        current_user = self.app_state.current_user
        if current_user:
            self.current_user_id = current_user["id"]
        else:
            # Fallback to API call if not in state
            user_resp = self.chat_app.api_client.get_current_user()
            if user_resp.success and user_resp.data:
                self.current_user_id = user_resp.data["id"]

        self.load_chat()

        # Ensure UI is rendered before loading messages
        self.update()

        # Load messages after UI is in place
        self.load_messages()

        # Subscribe to message updates for this chat via state manager
        self.app_state.subscribe(StateEvent.MESSAGE_RECEIVED, self._on_message_received)

        # Also keep the direct Redis subscription as backup/compatibility
        self.chat_app.api_client.subscribe_to_channel(
            self.chat_channel_name, self.process_new_message
        )
        self.logger.info(f"Subscribed to message updates for chat ID {self.chat_id}.")

    def will_unmount(self):
        """
        Called when the control is about to be removed from the page.
        """
        self.logger.info(f"ChatScreen for chat ID {self.chat_id} will unmount.")

        # Unsubscribe from state changes
        self.app_state.unsubscribe(
            StateEvent.MESSAGE_RECEIVED, self._on_message_received
        )

        # Unsubscribe from this chat's channel
        self.chat_app.api_client.unsubscribe_from_channel(self.chat_channel_name)
        self.logger.info(
            f"Unsubscribed from message updates for chat ID {self.chat_id}."
        )

    def _on_message_received(self, data):
        """Handle message received from state manager."""
        message = data.get("message")
        if message and message.get("chat_id") == self.chat_id:
            self.logger.info(
                f"Received message via state manager for chat {self.chat_id}"
            )
            self.process_new_message(json.dumps(message))

    def process_new_message(self, data):
        """
        Processes new messages (or updates) received from Redis for this chat.
        """
        try:
            message = json.loads(data)
            self.logger.info(
                f"Received new message for chat ID {self.chat_id}: {message}"
            )

            # Look for an existing row containing this message ID
            existing_message_row = next(
                (
                    row_control
                    for row_control in self.message_list.controls
                    if isinstance(row_control, ft.Row)
                    and len(row_control.controls) > 0
                    and isinstance(row_control.controls[0], ft.GestureDetector)
                    and row_control.controls[0].content is not None
                    and isinstance(row_control.controls[0].content, ft.Container)
                    and row_control.controls[0].content.data == message["id"]
                ),
                None,
            )

            if existing_message_row:
                # Update existing message (e.g., edited or status changed)
                self.update_message_in_list(existing_message_row, message)
                self.logger.info(f"Updated existing message {message['id']} in UI")
            elif message["user"]["id"] != self.current_user_id:
                # Add new message only if it's not from the current user
                # (current user's messages are added immediately in send_message)
                self.add_message_to_list(message)
                self.logger.info(
                    f"Added new message {message['id']} from other user to UI"
                )
            else:
                self.logger.info(
                    f"Skipping message {message['id']} from current user (already added)"
                )

            # Only auto-scroll if user is at bottom
            if self._should_auto_scroll():
                self.scroll_to_bottom()
            self.chat_app.page.update()

            # Mark the new message as read if it's not from the current user
            if message["user"]["id"] != self.current_user_id:
                threading.Thread(
                    target=self.mark_message_as_read, args=(message["id"],), daemon=True
                ).start()

        except json.JSONDecodeError:
            self.logger.error(f"Failed to decode message: {data}")
        except Exception as e:
            self.logger.error(f"Error processing new message: {e!s}")

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
        if (
            not isinstance(message_container, ft.Container)
            or not message_container.content
        ):
            return

        column_content = message_container.content  # a ft.Column([...])
        if (
            not isinstance(column_content, ft.Column)
            or len(column_content.controls) < 3
        ):
            return

        message_text = column_content.controls[1]  # ft.Text(content or <deleted>)
        time_info = column_content.controls[2]  # ft.Row([... time info ...])

        is_current_user = updated_message["user"]["id"] == self.current_user_id
        text_color = ft.colors.WHITE if is_current_user else ft.colors.BLACK

        if updated_message["is_deleted"]:
            message_text.value = "<This message has been deleted>"
            message_text.color = ft.colors.GREY_400
        else:
            message_text.value = updated_message["content"]
            message_text.color = text_color

        # Update the time info
        message_time = datetime.fromisoformat(updated_message["created_at"])
        formatted_time = message_time.strftime("%H:%M")
        if len(time_info.controls) > 0:
            time_info.controls[0].value = formatted_time

        # If message was edited
        if (
            updated_message.get("updated_at")
            and updated_message["updated_at"] != updated_message["created_at"]
        ):
            edit_time = datetime.fromisoformat(updated_message["updated_at"])
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
                        color=ft.colors.GREY_400
                        if is_current_user
                        else ft.colors.GREY_700,
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
            self.chat_name.value = response.data["name"]
            self.update()
            self.logger.info(f"Chat details loaded for chat ID {self.chat_id}")
        else:
            self.chat_app.show_error_dialog("Error Loading Chat", response.error)
            self.logger.error(
                f"Failed to load chat details for chat ID {self.chat_id}: {response.error}"
            )

    def send_message(self, e):
        """
        Sends a new message via the API.
        """
        if self.message_input.value.strip():
            message_content = self.message_input.value.strip()
            self.logger.info(f"Sending new message in chat ID {self.chat_id}")
            response = self.chat_app.api_client.send_message(
                self.chat_id, message_content
            )
            if response.success:
                # Clear input immediately
                self.message_input.value = ""
                self.message_input.update()

                # Add the message to the UI immediately
                message_data = response.data
                self.add_message_to_list(message_data)
                self.scroll_to_bottom()
                self.update()

                self.logger.info(
                    f"Message sent and added to UI for chat ID {self.chat_id}"
                )
            else:
                self.chat_app.show_error_dialog("Error Sending Message", response.error)
                self.logger.error(
                    f"Failed to send message in chat ID {self.chat_id}: {response.error}"
                )

    def load_messages(self, preserve_scroll_position=False):
        """
        Loads messages from the server, populates self.message_list,
        and marks unread messages as read. Implements smart scrolling to unread messages.

        Args:
            preserve_scroll_position: If True, maintains current scroll position instead of smart scrolling
        """
        self.logger.info(f"Loading messages for chat ID {self.chat_id}")

        # Store current scroll state if preserving
        should_preserve_scroll = preserve_scroll_position
        was_at_bottom = self.user_is_at_bottom if preserve_scroll_position else False

        response = self.chat_app.api_client.get_messages(self.chat_id)
        if response.success:
            self.message_list.controls.clear()
            self.first_unread_message_index = None

            if not response.data:
                self.message_list.controls.append(
                    ft.Text(
                        "No messages yet. Start a conversation!",
                        style=ft.TextThemeStyle.BODY_LARGE,
                        color=ft.colors.GREY_500,
                    )
                )
                self.logger.info(f"No messages found for chat ID {self.chat_id}")
            else:
                unread_message_ids = []
                first_unread_found = False

                # We reverse the list so older messages appear at the top
                reversed_messages = list(reversed(response.data))

                for index, msg in enumerate(reversed_messages):
                    self.add_message_to_list(msg)

                    # Check if the message is unread by the current user
                    is_unread = not msg["is_deleted"] and not any(
                        st["is_read"]
                        for st in msg["statuses"]
                        if st["user_id"] == self.current_user_id
                    )

                    if is_unread:
                        unread_message_ids.append(msg["id"])
                        # Track the first unread message for smart scrolling
                        if not first_unread_found:
                            self.first_unread_message_index = index
                            first_unread_found = True

                self.logger.info(
                    f"Loaded {len(response.data)} messages for chat {self.chat_id}"
                )

                # Handle scrolling based on preserve_scroll_position flag
                if should_preserve_scroll:
                    # If user was at bottom, keep them at bottom; otherwise don't scroll
                    if was_at_bottom:
                        self.scroll_to_bottom()
                        self.logger.info(
                            "Maintained bottom position after message reload"
                        )
                    else:
                        # Don't auto-scroll - user was in the middle of reading
                        self.logger.info(
                            "Preserved scroll position after message reload - no auto-scroll"
                        )
                elif unread_message_ids:
                    # Implement smart scrolling like in Telegram
                    self.logger.info(f"Found {len(unread_message_ids)} unread messages")
                    self._smart_scroll_to_unread()
                else:
                    # No unread messages, scroll to bottom
                    self.scroll_to_bottom()

                # Mark unread messages as read in background
                if unread_message_ids:
                    self.logger.info(
                        f"Marking {len(unread_message_ids)} messages as read for chat {self.chat_id}"
                    )
                    threading.Thread(
                        target=self.mark_messages_as_read,
                        args=(unread_message_ids,),
                        daemon=True,
                    ).start()

            self.update()
        else:
            self.chat_app.show_error_dialog("Error Loading Messages", response.error)
            self.logger.error(
                f"Failed to load messages for chat {self.chat_id}: {response.error}"
            )

    def _create_message_content(self, message, text_color):
        """
        Creates the message content widget based on whether the message is deleted or not.
        """
        if message["is_deleted"]:
            return ft.Text(
                "<This message has been deleted>",
                style=ft.TextThemeStyle.BODY_MEDIUM,
                color=ft.colors.GREY_400,
            )
        else:
            return ft.Text(
                message["content"],
                style=ft.TextThemeStyle.BODY_MEDIUM,
                color=text_color,
            )

    def _create_time_info(self, message, is_current_user):
        """
        Creates the time information widget, including edit/delete time if applicable.
        """
        message_time = datetime.fromisoformat(message["created_at"])
        formatted_time = message_time.strftime("%H:%M")

        time_info = ft.Row(
            [
                ft.Text(
                    formatted_time,
                    style=ft.TextThemeStyle.BODY_SMALL,
                    color=ft.colors.GREY_400 if is_current_user else ft.colors.GREY_700,
                )
            ],
            spacing=5,
        )

        # If the message has been deleted
        if message.get("is_deleted") and message.get("updated_at"):
            delete_time = datetime.fromisoformat(message["updated_at"])
            formatted_delete_time = delete_time.strftime("%H:%M")
            time_info.controls.append(
                ft.Text(
                    f"(deleted at {formatted_delete_time})",
                    style=ft.TextThemeStyle.BODY_SMALL,
                    italic=True,
                    color=ft.colors.GREY_400 if is_current_user else ft.colors.GREY_700,
                )
            )
        # If the message has been edited (and not deleted)
        elif (
            message.get("updated_at") and message["updated_at"] != message["created_at"]
        ):
            edit_time = datetime.fromisoformat(message["updated_at"])
            formatted_edit_time = edit_time.strftime("%H:%M")
            time_info.controls.append(
                ft.Text(
                    f"(edited at {formatted_edit_time})",
                    style=ft.TextThemeStyle.BODY_SMALL,
                    italic=True,
                    color=ft.colors.GREY_400 if is_current_user else ft.colors.GREY_700,
                )
            )

        return time_info

    def _create_message_widget(self, message):
        """
        Creates a complete message widget with all its components.
        Returns a Row containing the message.
        """
        is_current_user = message["user"]["id"] == self.current_user_id
        message_color = ft.colors.BLUE_700 if is_current_user else ft.colors.GREY_200
        text_color = ft.colors.WHITE if is_current_user else ft.colors.BLACK
        alignment = (
            ft.MainAxisAlignment.END if is_current_user else ft.MainAxisAlignment.START
        )

        # Create message content
        message_content = self._create_message_content(message, text_color)

        # Create time info
        time_info = self._create_time_info(message, is_current_user)

        # A Column with: [username, message_content, time_info]
        message_column = ft.Column(
            [
                ft.Text(
                    message["user"]["username"],
                    style=ft.TextThemeStyle.BODY_SMALL,
                    color=text_color,
                ),
                message_content,
                time_info,
            ]
        )

        # The Container storing message_column and `data=message['id']`
        message_container = ft.Container(
            content=message_column,
            bgcolor=message_color,
            border_radius=ft.border_radius.all(10),
            padding=10,
            width=300,
            data=message["id"],  # Store message ID in container's data
        )

        # A GestureDetector to handle long-press events (for edit/delete, read info, etc.)
        gesture_detector = ft.GestureDetector(
            content=message_container,
            on_long_press_start=lambda e: self.show_message_options(
                e, message, is_current_user
            ),
        )

        # Return a Row with the GestureDetector
        return ft.Row([gesture_detector], alignment=alignment)

    def _remove_placeholder_if_exists(self):
        """
        Removes the "No messages yet" placeholder if it exists.
        """
        if (
            len(self.message_list.controls) == 1
            and isinstance(self.message_list.controls[0], ft.Text)
            and "No messages yet" in self.message_list.controls[0].value
        ):
            self.message_list.controls.clear()

    def _add_to_chat_list(self, message_widget):
        """
        Adds the message widget to the chat list.
        """
        self.message_list.controls.append(message_widget)

    def _update_scroll_position(self):
        """
        Updates the scroll position to show the latest message.
        Note: Auto-scroll is handled by the ListView's auto_scroll property.
        """
        # The ListView has auto_scroll=True, so new messages automatically scroll to bottom
        # This method is here for potential future scroll position customization
        pass

    def _handle_read_status(self, message_data):
        """
        Handles read status for the message if it's from another user.
        """
        # Read status handling is implemented in process_new_message method
        # This is a placeholder for potential future read status logic
        pass

    def add_message_to_list(self, message):
        """
        Creates a new message widget and adds it to the message list.
        This method orchestrates the message creation process.
        """
        # Remove placeholder if it exists
        self._remove_placeholder_if_exists()

        # Create the message widget
        message_widget = self._create_message_widget(message)

        # Add to chat list
        self._add_to_chat_list(message_widget)

        # Update scroll position (handled automatically)
        self._update_scroll_position()

        # Handle read status
        self._handle_read_status(message)

        self.logger.info(
            f"Added message (ID: {message['id']}) to the message list for chat ID {self.chat_id}"
        )

    def _smart_scroll_to_unread(self):
        """
        Smart scrolling like in Telegram: scroll to first unread message or to bottom
        depending on the amount of unread messages and viewport height.
        """
        if self.first_unread_message_index is None:
            # No unread messages, scroll to bottom
            self.scroll_to_bottom()
            return

        total_messages = len(self.message_list.controls)

        # If the first unread message is close to the bottom (within last 5 messages)
        # or if most messages are unread, scroll to bottom for better UX
        messages_from_bottom = total_messages - self.first_unread_message_index

        if (
            messages_from_bottom <= 5
            or self.first_unread_message_index < total_messages * 0.3
        ):
            self.logger.info("Scrolling to bottom (unread messages are near end)")
            self.scroll_to_bottom()
        else:
            # Scroll to the first unread message
            self.logger.info(
                f"Scrolling to first unread message at index {self.first_unread_message_index}"
            )
            self.scroll_to_message(self.first_unread_message_index)

        self.user_is_at_bottom = messages_from_bottom <= 1

    def scroll_to_bottom(self):
        """
        Scroll the ListView to the bottom (offset=-1) if there are any messages.
        """
        if len(self.message_list.controls) > 0:
            self.message_list.scroll_to(
                offset=-1, duration=300, curve=ft.AnimationCurve.EASE_OUT
            )
            self.user_is_at_bottom = True

    def scroll_to_message(self, message_index):
        """
        Scroll to a specific message by index.
        """
        if 0 <= message_index < len(self.message_list.controls):
            # Calculate offset based on message index
            # Flet's scroll_to uses offset where 0 is top, -1 is bottom
            # For a specific index, we calculate the relative position
            total_messages = len(self.message_list.controls)
            offset = message_index / total_messages if total_messages > 0 else 0

            self.message_list.scroll_to(
                offset=offset, duration=300, curve=ft.AnimationCurve.EASE_OUT
            )
            self.user_is_at_bottom = message_index >= total_messages - 2

    def _on_scroll_change(self, e):
        """
        Track when user manually scrolls to determine if we should auto-scroll.
        """
        # Check if user is near the bottom of the scroll area
        # In Flet, the scroll offset goes from 0 (top) to the height of the content
        if hasattr(e.control, "scroll_offset") and hasattr(e.control, "visible_height"):
            scroll_position = e.control.scroll_offset
            visible_height = e.control.visible_height
            content_height = (
                len(self.message_list.controls) * 60
            )  # Approximate message height

            # Consider "at bottom" if within 100 pixels of the bottom
            self.user_is_at_bottom = (
                scroll_position + visible_height >= content_height - 100
            )
        else:
            # Fallback: assume user is at bottom if they scroll to the very end
            self.user_is_at_bottom = (
                (e.control.scroll_offset >= e.control.scroll_offset_max - 10)
                if hasattr(e.control, "scroll_offset_max")
                else True
            )

    def _should_auto_scroll(self):
        """
        Determine if we should auto-scroll when new messages arrive.
        Only auto-scroll if user is at or near the bottom.
        """
        return self.user_is_at_bottom

    def mark_message_as_read(self, message_id):
        """
        Mark a single message as read, calling the API. Runs in a background thread.
        """
        self.logger.info(f"Marking message ID {message_id} as read")
        response = self.chat_app.api_client.update_message_status(
            message_id, {"is_read": True}
        )
        if not response.success:
            self.logger.error(
                f"Failed to mark message {message_id} as read: {response.error}"
            )

    def mark_messages_as_read(self, message_ids):
        """
        Mark multiple messages as read in a loop.
        """
        self.logger.info(
            f"Marking {len(message_ids)} messages as read for chat {self.chat_id}"
        )
        for mid in message_ids:
            self.mark_message_as_read(mid)

    def show_message_options(self, e, message, is_current_user):
        """
        Show a dialog with read status info, plus 'Edit' / 'Delete' if it's the user's own message.
        """
        # Refresh the message status before showing options
        msg_resp = self.chat_app.api_client.get_messages(
            self.chat_id, limit=1, content=message["content"]
        )
        if msg_resp.success and msg_resp.data:
            updated_message = msg_resp.data[0]
        else:
            updated_message = message  # fallback if we can't fetch fresh data

        def close_dialog(_e):
            self.chat_app.page.close(options_dialog)

        # "Read by:" section
        read_status_title = ft.Text(
            "Read by:", style=ft.TextThemeStyle.TITLE_SMALL, weight=ft.FontWeight.BOLD
        )
        read_status_list = ft.ListView(spacing=5, expand=True)

        # For each user status, find username and read time
        for status in updated_message["statuses"]:
            # We need the username from the chat membership list
            chat_info = self.chat_app.api_client.get_chat(self.chat_id)
            if not chat_info.success:
                continue
            members = chat_info.data["members"]
            reader_name = next(
                (m["username"] for m in members if m["id"] == status["user_id"]),
                "Unknown",
            )

            if status["is_read"]:
                read_time = None
                if status["read_at"]:
                    read_time = datetime.fromisoformat(status["read_at"])
                formatted_time = (
                    read_time.strftime("%Y-%m-%d %H:%M:%S") if read_time else "Unknown"
                )
                read_status_list.controls.append(
                    ft.Text(
                        f"{reader_name}: {formatted_time}",
                        style=ft.TextThemeStyle.BODY_SMALL,
                    )
                )
            else:
                read_status_list.controls.append(
                    ft.Text(
                        f"{reader_name}: Unread", style=ft.TextThemeStyle.BODY_SMALL
                    )
                )

        read_status_container = ft.Container(
            content=ft.Column([read_status_title, read_status_list], expand=True),
            padding=10,
        )

        options = [read_status_container]

        if is_current_user and not updated_message["is_deleted"]:
            options.extend(
                [
                    ft.Divider(),
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.EDIT),
                        title=ft.Text("Edit", style=ft.TextThemeStyle.TITLE_MEDIUM),
                        subtitle=ft.Text(
                            "Modify your message", style=ft.TextThemeStyle.BODY_SMALL
                        ),
                        on_click=lambda _: self.edit_message(updated_message),
                    ),
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.DELETE),
                        title=ft.Text("Delete", style=ft.TextThemeStyle.TITLE_MEDIUM),
                        subtitle=ft.Text(
                            "Remove this message", style=ft.TextThemeStyle.BODY_SMALL
                        ),
                        on_click=lambda _: self.delete_message(updated_message),
                    ),
                ]
            )

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
                    message["id"], {"content": new_content.value.strip()}
                )
                if resp.success:
                    self.load_messages(preserve_scroll_position=True)
                    self.chat_app.page.close(dialog)
                else:
                    self.chat_app.show_error_dialog(
                        "Error Updating Message", resp.error
                    )
            else:
                self.chat_app.show_error_dialog(
                    "Invalid Input", {"detail": "Please enter message content."}
                )

        new_content = ft.TextField(value=message["content"], multiline=True)
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
            resp = self.chat_app.api_client.delete_message(message["id"])
            if resp.success:
                self.load_messages(preserve_scroll_position=True)
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
