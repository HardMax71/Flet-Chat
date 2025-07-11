import json
import logging
import threading
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from threading import RLock


class StateEvent(Enum):
    """Events that can trigger state changes."""

    USER_LOGGED_IN = "user_logged_in"
    USER_LOGGED_OUT = "user_logged_out"
    USER_UPDATED = "user_updated"
    CHATS_LOADED = "chats_loaded"
    CHAT_ADDED = "chat_added"
    CHAT_UPDATED = "chat_updated"
    CHAT_DELETED = "chat_deleted"
    UNREAD_COUNT_UPDATED = "unread_count_updated"
    MESSAGE_RECEIVED = "message_received"
    CURRENT_CHAT_CHANGED = "current_chat_changed"
    CONNECTION_STATUS_CHANGED = "connection_status_changed"


class AppState:
    """
    Centralized application state store using observer pattern.
    Thread-safe singleton that manages all application state.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls) -> "AppState":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return

        self._initialized = True
        self._instance_lock: "RLock" = threading.RLock()

        # Configure logging
        self.logger = logging.getLogger("AppState")
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s:%(name)s: %(message)s"
        )
        handler.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(handler)

        # State data
        self._current_user: Optional[Dict[str, Any]] = None
        self._is_authenticated: bool = False
        self._chats: List[Dict[str, Any]] = []
        self._current_chat_id: Optional[int] = None
        self._unread_counts: Dict[int, int] = {}  # chat_id -> unread_count
        self._is_connected: bool = True

        # Observer callbacks: event -> list of callbacks
        self._observers: Dict[StateEvent, List[Callable]] = {
            event: [] for event in StateEvent
        }

    # Observer pattern methods
    def subscribe(
        self, event: StateEvent, callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """Subscribe to state changes for a specific event."""
        with self._instance_lock:
            if callback not in self._observers[event]:
                self._observers[event].append(callback)
                self.logger.info(f"Subscribed to {event.value}")

    def unsubscribe(
        self, event: StateEvent, callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """Unsubscribe from state changes for a specific event."""
        with self._instance_lock:
            if callback in self._observers[event]:
                self._observers[event].remove(callback)
                self.logger.info(f"Unsubscribed from {event.value}")

    def _notify_observers(self, event: StateEvent, data: Dict[str, Any]) -> None:
        """Notify all observers of a state change."""
        with self._instance_lock:
            observers = self._observers[
                event
            ].copy()  # Copy to avoid modification during iteration

        for callback in observers:
            try:
                callback(data)
            except Exception as e:
                self.logger.error(
                    f"Error in observer callback for {event.value}: {str(e)}"
                )

    # User state management
    @property
    def current_user(self) -> Optional[Dict[str, Any]]:
        with self._instance_lock:
            return self._current_user.copy() if self._current_user else None

    @property
    def is_authenticated(self) -> bool:
        with self._instance_lock:
            return self._is_authenticated

    def set_current_user(self, user: Dict[str, Any]) -> None:
        """Set the current user and notify observers."""
        with self._instance_lock:
            self._current_user = user.copy() if user else None
            self._is_authenticated = user is not None

        event = StateEvent.USER_LOGGED_IN if user else StateEvent.USER_LOGGED_OUT
        self._notify_observers(event, {"user": self._current_user})
        self.logger.info(f"User state changed: {event.value}")

    def update_current_user(self, user_updates: Dict[str, Any]) -> None:
        """Update current user information and notify observers."""
        with self._instance_lock:
            if self._current_user:
                self._current_user.update(user_updates)
                user_data = self._current_user.copy()
            else:
                return

        self._notify_observers(StateEvent.USER_UPDATED, {"user": user_data})
        self.logger.info("User information updated")

    def clear_user(self) -> None:
        """Clear user state (logout)."""
        with self._instance_lock:
            self._current_user = None
            self._is_authenticated = False
        self._notify_observers(StateEvent.USER_LOGGED_OUT, {})

    # Chat state management
    @property
    def chats(self) -> List[Dict[str, Any]]:
        with self._instance_lock:
            return [chat.copy() for chat in self._chats]

    @property
    def current_chat_id(self) -> Optional[int]:
        with self._instance_lock:
            return self._current_chat_id

    def set_chats(self, chats: List[Dict[str, Any]]) -> None:
        """Set the complete chat list and notify observers."""
        with self._instance_lock:
            self._chats = [chat.copy() for chat in chats] if chats else []
            chats_data = [chat.copy() for chat in self._chats]

        self._notify_observers(StateEvent.CHATS_LOADED, {"chats": chats_data})
        self.logger.info(f"Loaded {len(chats_data)} chats")

    def add_chat(self, chat: Dict[str, Any]) -> None:
        """Add a new chat and notify observers."""
        with self._instance_lock:
            chat_copy = chat.copy()
            self._chats.append(chat_copy)

        self._notify_observers(StateEvent.CHAT_ADDED, {"chat": chat_copy})
        self.logger.info(f"Added chat: {chat.get('name', 'Unknown')}")

    def update_chat(self, chat_id: int, updates: Dict[str, Any]) -> None:
        """Update an existing chat and notify observers."""
        with self._instance_lock:
            for i, chat in enumerate(self._chats):
                if chat.get("id") == chat_id:
                    self._chats[i].update(updates)
                    updated_chat = self._chats[i].copy()
                    break
            else:
                return  # Chat not found

        self._notify_observers(
            StateEvent.CHAT_UPDATED,
            {"chat_id": chat_id, "chat": updated_chat, "updates": updates},
        )
        self.logger.info(f"Updated chat {chat_id}")

    def remove_chat(self, chat_id: int) -> None:
        """Remove a chat and notify observers."""
        with self._instance_lock:
            removed_chat = None
            for i, chat in enumerate(self._chats):
                if chat.get("id") == chat_id:
                    removed_chat = self._chats.pop(i)
                    break

            if not removed_chat:
                return  # Chat not found

        self._notify_observers(
            StateEvent.CHAT_DELETED, {"chat_id": chat_id, "chat": removed_chat}
        )
        self.logger.info(f"Removed chat {chat_id}")

    def set_current_chat(self, chat_id: Optional[int]) -> None:
        """Set the currently active chat and notify observers."""
        with self._instance_lock:
            old_chat_id = self._current_chat_id
            self._current_chat_id = chat_id

        if old_chat_id != chat_id:
            self._notify_observers(
                StateEvent.CURRENT_CHAT_CHANGED,
                {"old_chat_id": old_chat_id, "new_chat_id": chat_id},
            )
            self.logger.info(f"Current chat changed from {old_chat_id} to {chat_id}")

    # Unread count management
    @property
    def unread_counts(self) -> Dict[int, int]:
        with self._instance_lock:
            return self._unread_counts.copy()

    def get_unread_count(self, chat_id: int) -> int:
        """Get unread count for a specific chat."""
        with self._instance_lock:
            return self._unread_counts.get(chat_id, 0)

    def update_unread_count(self, chat_id: int, count: int) -> None:
        """Update unread count for a specific chat and notify observers."""
        with self._instance_lock:
            old_count = self._unread_counts.get(chat_id, 0)
            self._unread_counts[chat_id] = count

        if old_count != count:
            self._notify_observers(
                StateEvent.UNREAD_COUNT_UPDATED,
                {"chat_id": chat_id, "old_count": old_count, "new_count": count},
            )
            self.logger.info(f"Unread count for chat {chat_id}: {old_count} -> {count}")

    # Connection status
    @property
    def is_connected(self) -> bool:
        with self._instance_lock:
            return self._is_connected

    def set_connection_status(self, connected: bool) -> None:
        """Set connection status and notify observers."""
        with self._instance_lock:
            old_status = self._is_connected
            self._is_connected = connected

        if old_status != connected:
            self._notify_observers(
                StateEvent.CONNECTION_STATUS_CHANGED,
                {"old_status": old_status, "new_status": connected},
            )
            self.logger.info(f"Connection status changed: {connected}")

    # Utility methods
    def get_chat_by_id(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific chat by ID."""
        with self._instance_lock:
            for chat in self._chats:
                if chat.get("id") == chat_id:
                    return chat.copy()
            return None

    def clear_all_state(self) -> None:
        """Clear all state (for logout)."""
        with self._instance_lock:
            self._current_user = None
            self._is_authenticated = False
            self._chats = []
            self._current_chat_id = None
            self._unread_counts = {}
            self._is_connected = True

        self.logger.info("All state cleared")


class StateManager:
    """
    Coordinates between API client, Redis updates, and application state.
    Acts as a bridge between the data layer and the UI layer.
    """

    def __init__(self, api_client) -> None:
        self.api_client = api_client
        self.app_state = AppState()

        # Configure logging
        self.logger = logging.getLogger("StateManager")
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s:%(name)s: %(message)s"
        )
        handler.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(handler)

        # Track Redis subscriptions
        self._subscriptions: Dict[str, bool] = {}

    def initialize(self) -> None:
        """Initialize state manager and load initial data if authenticated."""
        if self.api_client.is_authenticated():
            self.load_initial_data()

    def load_initial_data(self) -> None:
        """Load user and chat data from API."""
        # Load current user
        user_response = self.api_client.get_current_user()
        if user_response.success:
            self.app_state.set_current_user(user_response.data)
            self.setup_real_time_subscriptions()
        else:
            self.logger.error(f"Failed to load current user: {user_response.error}")
            return

        # Load chats
        chats_response = self.api_client.get_chats()
        if chats_response.success:
            self.app_state.set_chats(chats_response.data or [])
            self.load_unread_counts(chats_response.data or [])
        else:
            self.logger.error(f"Failed to load chats: {chats_response.error}")

    def load_unread_counts(self, chats: List[Dict[str, Any]]) -> None:
        """Load unread message counts for all chats."""
        for chat in chats:
            chat_id = chat.get("id")
            if chat_id:
                count_response = self.api_client.get_unread_messages_count(chat_id)
                if count_response.success:
                    self.app_state.update_unread_count(chat_id, count_response.data)

    def setup_real_time_subscriptions(self) -> None:
        """Set up Redis subscriptions for real-time updates."""
        current_user = self.app_state.current_user
        if not current_user:
            return

        user_id = current_user.get("id")
        if not user_id:
            return

        # Subscribe to unread count updates for each chat
        for chat in self.app_state.chats:
            chat_id = chat.get("id")
            if chat_id:
                self.subscribe_to_unread_count(chat_id, user_id)

    def subscribe_to_unread_count(self, chat_id: int, user_id: int) -> None:
        """Subscribe to unread count updates for a specific chat."""
        channel_name = f"chat:{chat_id}:unread_count:{user_id}"
        if channel_name not in self._subscriptions:
            self.api_client.subscribe_to_channel(
                channel_name, self._handle_unread_count_update
            )
            self._subscriptions[channel_name] = True
            self.logger.info(f"Subscribed to unread count updates for chat {chat_id}")

    def subscribe_to_chat_messages(self, chat_id: int) -> None:
        """Subscribe to new messages for a specific chat."""
        channel_name = f"chat:{chat_id}"
        if channel_name not in self._subscriptions:
            self.api_client.subscribe_to_channel(
                channel_name, self._handle_message_update
            )
            self._subscriptions[channel_name] = True
            self.logger.info(f"Subscribed to messages for chat {chat_id}")

    def unsubscribe_from_chat_messages(self, chat_id: int) -> None:
        """Unsubscribe from messages for a specific chat."""
        channel_name = f"chat:{chat_id}"
        if channel_name in self._subscriptions:
            self.api_client.unsubscribe_from_channel(channel_name)
            del self._subscriptions[channel_name]
            self.logger.info(f"Unsubscribed from messages for chat {chat_id}")

    def _handle_unread_count_update(self, data: str) -> None:
        """Handle Redis unread count updates."""
        try:
            message = json.loads(data)
            chat_id = message.get("chat_id")
            unread_count = message.get("unread_count", 0)
            user_id = message.get("user_id")

            current_user = self.app_state.current_user
            if current_user and user_id == current_user.get("id"):
                self.app_state.update_unread_count(chat_id, unread_count)

        except (json.JSONDecodeError, KeyError) as e:
            self.logger.error(f"Error processing unread count update: {str(e)}")

    def _handle_message_update(self, data: str) -> None:
        """Handle Redis message updates."""
        try:
            message = json.loads(data)
            self.app_state._notify_observers(
                StateEvent.MESSAGE_RECEIVED, {"message": message}
            )
        except json.JSONDecodeError as e:
            self.logger.error(f"Error processing message update: {str(e)}")

    # Public API for state management operations
    def login_user(self, user_data: Dict[str, Any]) -> None:
        """Handle successful user login."""
        self.app_state.set_current_user(user_data)
        self.load_initial_data()

    def logout_user(self) -> None:
        """Handle user logout."""
        # Unsubscribe from all Redis channels
        for channel_name in list(self._subscriptions.keys()):
            self.api_client.unsubscribe_from_channel(channel_name)
        self._subscriptions.clear()

        # Clear application state
        self.app_state.clear_all_state()

    def refresh_chats(self) -> bool:
        """Refresh chat list from API."""
        chats_response = self.api_client.get_chats()
        if chats_response.success:
            self.app_state.set_chats(chats_response.data or [])
            self.load_unread_counts(chats_response.data or [])
            return True
        return False

    def add_chat(self, chat_data: Dict[str, Any]) -> None:
        """Add a new chat and set up subscriptions."""
        self.app_state.add_chat(chat_data)

        # Set up subscriptions for the new chat
        current_user = self.app_state.current_user
        if current_user and chat_data.get("id"):
            self.subscribe_to_unread_count(chat_data["id"], current_user["id"])

    def remove_chat(self, chat_id: int) -> None:
        """Remove a chat and clean up subscriptions."""
        current_user = self.app_state.current_user
        if current_user:
            # Unsubscribe from chat channels
            unread_channel = f"chat:{chat_id}:unread_count:{current_user['id']}"
            message_channel = f"chat:{chat_id}"

            for channel in [unread_channel, message_channel]:
                if channel in self._subscriptions:
                    self.api_client.unsubscribe_from_channel(channel)
                    del self._subscriptions[channel]

        self.app_state.remove_chat(chat_id)

    def set_current_chat(self, chat_id: Optional[int]) -> None:
        """Set the current active chat and manage message subscriptions."""
        old_chat_id = self.app_state.current_chat_id

        # Unsubscribe from old chat messages
        if old_chat_id:
            self.unsubscribe_from_chat_messages(old_chat_id)

        # Subscribe to new chat messages
        if chat_id:
            self.subscribe_to_chat_messages(chat_id)

        self.app_state.set_current_chat(chat_id)
