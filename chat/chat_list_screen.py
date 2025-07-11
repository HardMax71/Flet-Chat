import logging

import flet as ft

from .state_manager import AppState, StateEvent


class ChatListScreen(ft.Column):
    def __init__(self, chat_app):
        super().__init__()
        self.chat_app = chat_app
        self.app_state = AppState()

        # Performance optimization: cache for incremental updates
        self.chat_tiles_cache = {}  # chat_id -> ListTile mapping
        self.chats_data = {}  # chat_id -> chat_data mapping

        # Configure logging
        self.logger = logging.getLogger("ChatListScreen")
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s:%(name)s: %(message)s"
        )
        handler.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(handler)

        # Subscribe to state changes
        self.app_state.subscribe(StateEvent.CHATS_LOADED, self._on_chats_loaded)
        self.app_state.subscribe(StateEvent.CHAT_ADDED, self._on_chat_added)
        self.app_state.subscribe(StateEvent.CHAT_UPDATED, self._on_chat_updated)
        self.app_state.subscribe(StateEvent.CHAT_DELETED, self._on_chat_deleted)
        self.app_state.subscribe(
            StateEvent.UNREAD_COUNT_UPDATED, self._on_unread_count_updated
        )

        # GUI elements
        self.loading_indicator = ft.ProgressRing(visible=False)
        self.user_search_combobox = ft.Dropdown(
            hint_text="Search users to start a new chat",
            editable=True,
            enable_search=True,
            enable_filter=True,
            width=1000,  # Set a large width that will be constrained by parent
            options=[],
            on_change=self.start_chat_with_user,
            on_focus=self.on_search_focus,
            on_blur=self.on_search_blur,
        )

        self.chat_list = ft.ListView(spacing=10, expand=True)
        self.loading_container = ft.Container(
            content=ft.Column(
                [
                    ft.ProgressRing(),
                    ft.Text(
                        "Chats are being loaded...", style=ft.TextThemeStyle.BODY_MEDIUM
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            ),
            alignment=ft.alignment.center,
            expand=True,
            visible=False,
        )

    def build(self):
        """
        Builds the layout for ChatListScreen:
          - Top row with user profile, "Chats" title, and refresh button
          - Row with search input and button
          - A dropdown for search results
          - A stack with either the chat list or the loading container
        """
        self.controls = [
            ft.Row(
                [
                    ft.IconButton(
                        icon=ft.icons.PERSON,
                        on_click=self.show_profile,
                        tooltip="Profile",
                    ),
                    ft.Text("Chats", style=ft.TextThemeStyle.HEADLINE_MEDIUM),
                    ft.IconButton(
                        icon=ft.icons.REFRESH,
                        on_click=self.load_chats,
                        tooltip="Refresh",
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Container(
                content=self.user_search_combobox,
                alignment=ft.alignment.center_left,
                expand_loose=True,
            ),
            ft.Stack([self.chat_list, self.loading_container], expand=True),
        ]
        self.expand = True
        self.spacing = 20

    def _on_chats_loaded(self, data):
        """Handle chats loaded state change."""
        chats = data.get("chats", [])
        self.logger.info(f"Received chats loaded event with {len(chats)} chats")
        self._populate_chat_list(chats)

    def _on_chat_added(self, data):
        """Handle new chat added state change."""
        chat = data.get("chat")
        if chat:
            self.logger.info(
                f"Received chat added event: {chat.get('name', 'Unknown')}"
            )
            self._add_single_chat_to_list(chat)

    def _on_chat_updated(self, data):
        """Handle chat updated state change."""
        chat_id = data.get("chat_id")
        chat = data.get("chat")
        if chat_id and chat:
            self.logger.info(f"Received chat updated event for chat {chat_id}")
            self._update_single_chat_in_list(chat_id, chat)

    def _on_chat_deleted(self, data):
        """Handle chat deleted state change."""
        chat_id = data.get("chat_id")
        if chat_id:
            self.logger.info(f"Received chat deleted event for chat {chat_id}")
            self._remove_single_chat_from_list(chat_id)

    def _on_unread_count_updated(self, data):
        """Handle unread count updated state change."""
        chat_id = data.get("chat_id")
        new_count = data.get("new_count", 0)
        if chat_id is not None:
            self.logger.info(
                f"Received unread count update for chat {chat_id}: {new_count}"
            )
            self.update_chat_unread_count(chat_id, new_count)

    def did_mount(self):
        """
        Called when ChatListScreen is first mounted to the page.
        Load chats from state or refresh if needed.
        """
        self.logger.info("ChatListScreen mounted. Loading chats...")

        # Check if we have chats in state
        chats = self.app_state.chats
        if chats:
            self.logger.info(f"Loading {len(chats)} chats from state")
            self._populate_chat_list(chats)
        else:
            # Refresh chats from API
            self.load_chats()

    def will_unmount(self):
        """
        Called when ChatListScreen is about to be removed from the page.
        Unsubscribe from state changes.
        """
        self.logger.info(
            "ChatListScreen will unmount. Unsubscribing from state changes..."
        )

        # Unsubscribe from state changes
        self.app_state.unsubscribe(StateEvent.CHATS_LOADED, self._on_chats_loaded)
        self.app_state.unsubscribe(StateEvent.CHAT_ADDED, self._on_chat_added)
        self.app_state.unsubscribe(StateEvent.CHAT_UPDATED, self._on_chat_updated)
        self.app_state.unsubscribe(StateEvent.CHAT_DELETED, self._on_chat_deleted)
        self.app_state.unsubscribe(
            StateEvent.UNREAD_COUNT_UPDATED, self._on_unread_count_updated
        )

    def create_chat_tile(self, chat, unread_count=None):
        """
        Creates a chat tile for a given chat data.
        Returns the ListTile and caches it for future updates.
        """
        chat_id = chat["id"]

        # Get current user from state
        current_user = self.app_state.current_user
        if not current_user:
            self.logger.error("Cannot create chat tile: no current user in state")
            return None

        current_user_id = current_user["id"]

        # Get unread count if not provided
        if unread_count is None:
            unread_count = self.app_state.get_unread_count(chat_id)

        chat_name = ft.Text(chat["name"], style=ft.TextThemeStyle.TITLE_MEDIUM)

        # Prepare the list of chat members with smart display
        members = []
        for member in chat["members"]:
            if member["id"] == current_user_id:
                members.append("You")
            else:
                # Truncate long usernames to max 10 characters for space efficiency
                username = member["username"]
                if len(username) > 10:
                    username = username[:10] + "…"
                members.append(username)

        # Show first 3 members + count for remaining
        if len(members) <= 3:
            members_display = ", ".join(members)
        else:
            first_three = members[:3]
            remaining_count = len(members) - 3
            members_display = f"{', '.join(first_three)}, +{remaining_count}"

        members_text = ft.Text(
            members_display,
            style=ft.TextThemeStyle.BODY_SMALL,
            color=ft.colors.GREY_700,
        )

        # Create unread indicator
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
                        expand=True,
                    ),
                    unread_indicator,
                    ft.Row(
                        [
                            ft.IconButton(
                                icon=ft.icons.EDIT,
                                on_click=lambda _, c=chat: self.edit_chat(c),
                                tooltip="Edit chat",
                            ),
                            ft.IconButton(
                                icon=ft.icons.DELETE,
                                on_click=lambda _, c=chat: self.delete_chat(c),
                                tooltip="Delete chat",
                            ),
                        ],
                        spacing=0,
                        tight=True,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            on_click=lambda _, chat_id=chat_id: self.chat_app.show_chat(chat_id),
        )
        list_tile.data = chat  # store chat info
        list_tile.controls_dict = {"unread_indicator": unread_indicator}

        # Cache the tile and data
        self.chat_tiles_cache[chat_id] = list_tile
        self.chats_data[chat_id] = chat

        return list_tile

    def update_chat_unread_count(self, chat_id, new_unread_count):
        """
        Updates the unread count for a specific chat without reloading the entire list.
        """
        if chat_id in self.chat_tiles_cache:
            list_tile = self.chat_tiles_cache[chat_id]
            unread_indicator = list_tile.controls_dict.get("unread_indicator")

            if unread_indicator:
                # Update the unread count display
                unread_indicator.content.value = str(new_unread_count)
                unread_indicator.visible = new_unread_count > 0

                # Update the UI
                unread_indicator.update()
                self.logger.info(
                    f"Updated unread count for chat {chat_id}: {new_unread_count}"
                )
            else:
                self.logger.warning(
                    f"Could not find unread indicator for chat {chat_id}"
                )
        else:
            self.logger.warning(
                f"Chat {chat_id} not found in cache, falling back to full reload"
            )
            self.load_chats()

    def load_chats(self, e=None):
        """
        Refreshes the chat list from the API using state manager.
        """
        self.loading_container.visible = True
        self.chat_list.visible = False
        self.update()

        # Use state manager to refresh chats
        success = self.chat_app.state_manager.refresh_chats()
        if not success:
            self.chat_app.show_error_dialog(
                "Error Loading Chats", {"detail": "Failed to load chats from server"}
            )
            self.logger.error("Failed to refresh chats through state manager")

        self.loading_container.visible = False
        self.chat_list.visible = True
        self.update()

    def _populate_chat_list(self, chats):
        """
        Populates the chat list UI with the provided chats.
        """
        # Clear current UI and cache
        self.chat_list.controls.clear()
        self.chat_tiles_cache.clear()
        self.chats_data.clear()

        if not chats:
            self.chat_list.controls.append(
                ft.Text(
                    "No chats found. Search for users to start a new chat!",
                    style=ft.TextThemeStyle.BODY_LARGE,
                    color=ft.colors.GREY_500,
                )
            )
        else:
            # Get current user from state
            current_user = self.app_state.current_user
            if not current_user:
                self.chat_app.show_error_dialog(
                    "Error", {"detail": "User not authenticated."}
                )
                return

            # Populate chat list using the new tile creation method
            for chat in chats:
                unread_count = self.app_state.get_unread_count(chat["id"])
                list_tile = self.create_chat_tile(chat, unread_count)
                self.chat_list.controls.append(list_tile)

        self.update()
        self.logger.info(f"Populated chat list with {len(chats)} chats")

    def _add_single_chat_to_list(self, chat):
        """
        Add a single chat to the list (for real-time updates).
        """
        # Remove "no chats" message if present
        if (
            len(self.chat_list.controls) == 1
            and isinstance(self.chat_list.controls[0], ft.Text)
            and "No chats found" in self.chat_list.controls[0].value
        ):
            self.chat_list.controls.clear()

        unread_count = self.app_state.get_unread_count(chat["id"])
        list_tile = self.create_chat_tile(chat, unread_count)
        self.chat_list.controls.append(list_tile)
        self.update()

    def _update_single_chat_in_list(self, chat_id, updated_chat):
        """
        Update a single chat in the list (for real-time updates).
        """
        if chat_id in self.chat_tiles_cache:
            # Remove old tile
            old_tile = self.chat_tiles_cache[chat_id]
            if old_tile in self.chat_list.controls:
                self.chat_list.controls.remove(old_tile)

            # Add updated tile
            unread_count = self.app_state.get_unread_count(chat_id)
            new_tile = self.create_chat_tile(updated_chat, unread_count)
            self.chat_list.controls.append(new_tile)
            self.update()

    def _remove_single_chat_from_list(self, chat_id):
        """
        Remove a single chat from the list (for real-time updates).
        """
        if chat_id in self.chat_tiles_cache:
            tile = self.chat_tiles_cache[chat_id]
            if tile in self.chat_list.controls:
                self.chat_list.controls.remove(tile)

            # Clean up cache
            del self.chat_tiles_cache[chat_id]
            if chat_id in self.chats_data:
                del self.chats_data[chat_id]

            # Add "no chats" message if list is empty
            if not self.chat_list.controls:
                self.chat_list.controls.append(
                    ft.Text(
                        "No chats found. Search for users to start a new chat!",
                        style=ft.TextThemeStyle.BODY_LARGE,
                        color=ft.colors.GREY_500,
                    )
                )

            self.update()

    def edit_chat(self, chat):
        """
        Opens a dialog to rename the chat.
        """

        def update_chat_name(_e):
            if new_name.value.strip():
                response = self.chat_app.api_client.update_chat(
                    chat["id"], {"name": new_name.value.strip()}
                )
                if response.success:
                    self.load_chats()
                    self.chat_app.page.close(dialog)
                    self.logger.info(
                        f"Chat ID {chat['id']} renamed to '{new_name.value}'"
                    )
                else:
                    self.chat_app.show_error_dialog(
                        "Error Updating Chat", response.error
                    )
                    self.logger.error(
                        f"Failed to update chat ID {chat['id']}: {response.error}"
                    )
            else:
                self.chat_app.show_error_dialog(
                    "Invalid Input", {"detail": "Please enter a chat name."}
                )
                self.logger.warning(
                    "Attempted to update chat without providing a new name."
                )

        new_name = ft.TextField(value=chat["name"], label="Chat Name")
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Edit Chat Name"),
            content=new_name,
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: self.close_dialog(dialog)),
                ft.TextButton("Update", on_click=update_chat_name),
            ],
            on_dismiss=lambda _: self.close_dialog(dialog),
        )
        self.chat_app.page.open(dialog)
        self.logger.info(f"Opened edit chat dialog for chat ID {chat['id']}")

    def delete_chat(self, chat):
        """
        Opens a dialog to confirm chat deletion.
        """

        def confirm_delete(_e):
            response = self.chat_app.api_client.delete_chat(chat["id"])
            if response.success:
                # Remove the deleted chat from the chat list
                self.chat_list.controls = [
                    c
                    for c in self.chat_list.controls
                    if isinstance(c, ft.ListTile) and c.data["id"] != chat["id"]
                ]
                if not self.chat_list.controls:
                    self.chat_list.controls.append(
                        ft.Text(
                            "No chats found. Search for users to start a new chat!",
                            style=ft.TextThemeStyle.BODY_LARGE,
                            color=ft.colors.GREY_500,
                        )
                    )
                self.chat_app.page.update()
                self.chat_app.page.close(dialog)
                self.logger.info(f"Deleted chat ID {chat['id']} successfully.")
            else:
                self.chat_app.show_error_dialog("Error Deleting Chat", response.error)
                self.logger.error(
                    f"Failed to delete chat ID {chat['id']}: {response.error}"
                )

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Delete Chat"),
            content=ft.Text(
                f"Are you sure you want to delete the chat '{chat['name']}'?"
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: self.close_dialog(dialog)),
                ft.TextButton("Delete", on_click=confirm_delete),
            ],
            on_dismiss=lambda _: self.close_dialog(dialog),
        )
        self.chat_app.page.open(dialog)
        self.logger.info(f"Opened delete chat dialog for chat ID {chat['id']}")

    def show_profile(self, _e):
        """
        Navigates to the user's profile screen.
        """
        self.chat_app.show_user_profile()
        self.logger.info("Navigated to user profile.")

    def on_search_focus(self, _e):
        """
        Called when the search combobox gains focus.
        """
        self.logger.info("Search combobox focused")
        # Load all users when focus is gained
        self.load_all_users()

    def on_search_blur(self, _e):
        """
        Called when the search combobox loses focus.
        """
        self.logger.info("Search combobox lost focus")

    def load_all_users(self):
        """
        Loads all users for the combobox when focused.
        """
        self.logger.info("Loading all users for search combobox")
        response = self.chat_app.api_client.search_users(
            ""
        )  # Empty search to get all users
        if response.success:
            self.user_search_combobox.options.clear()
            if response.data:
                for user in response.data:
                    self.user_search_combobox.options.append(
                        ft.dropdown.Option(key=str(user["id"]), text=user["username"])
                    )
                self.logger.info(
                    f"Loaded {len(response.data)} users for search combobox."
                )
            else:
                self.user_search_combobox.options.append(
                    ft.dropdown.Option(key="no_users", text="No users found")
                )
                self.logger.info("No users found for search combobox.")
            self.user_search_combobox.update()
        else:
            self.chat_app.show_error_dialog("Error Loading Users", response.error)
            self.logger.error(f"Failed to load users: {response.error}")

    def start_chat_with_user(self, _e):
        """
        Triggered by user_search_combobox on_change.
        We attempt to start or load a chat with the selected user.
        Then we navigate to the new or existing chat screen.
        """
        selected_user_id = self.user_search_combobox.value
        if selected_user_id and selected_user_id not in ["no_users", ""]:
            self.logger.info(f"Starting chat with user ID {selected_user_id}")
            response = self.chat_app.api_client.start_chat(int(selected_user_id))
            if response.success:
                # Add chat to state manager
                chat_data = response.data
                self.chat_app.state_manager.add_chat(chat_data)

                # Clear out the search UI BEFORE navigating away:
                self.user_search_combobox.value = None
                self.user_search_combobox.options.clear()

                # Instead of calling self.update(), we call the page-level update
                # because we might be about to leave ChatListScreen
                self.chat_app.page.update()

                # Now that we cleaned up the search fields, let's go to the chat:
                self.chat_app.show_chat(chat_data["id"])
                self.logger.info(f"Chat started with user ID {selected_user_id}")
            else:
                self.chat_app.show_error_dialog("Error Starting Chat", response.error)
                self.logger.error(
                    f"Failed to start chat with user ID {selected_user_id}: {response.error}"
                )
        else:
            # Reset search if user chooses "no_users" or empty value
            self.user_search_combobox.value = None
            self.user_search_combobox.options.clear()
            self.chat_app.page.update()
            self.logger.info("Reset search combobox; no user selected.")

    def close_dialog(self, dialog):
        """
        Closes a dialog and forces a page update (if still mounted).
        """
        self.chat_app.page.close(dialog)
        self.logger.info("Closed dialog.")
