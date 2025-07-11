import json
import logging
import os
import queue
import threading
import time
from datetime import datetime, timedelta, timezone

import keyring
import pytz
import redis
import requests


class ApiResponse:
    def __init__(self, success, data=None, status_code=None, error=None):
        self.success = success
        self.data = data
        self.status_code = status_code
        self.error = error


class ApiClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.access_token = None
        self.refresh_token = None
        self.token_expiry = None
        self.subscriptions = {}

        # Configure logging
        self.logger = logging.getLogger("ApiClient")
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s:%(name)s: %(message)s"
        )
        handler.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(handler)

        REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
        REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))

        # Initialize Redis client with error handling
        try:
            self.redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=0,
                decode_responses=True,
                socket_connect_timeout=5,
            )
            self.redis_client.ping()  # Test the connection
            self.pubsub = self.redis_client.pubsub()
            self.message_queue = queue.Queue()
            self.subscriptions = {}
            self.pubsub_thread = threading.Thread(
                target=self._listen_to_pubsub, daemon=True
            )
            self.pubsub_thread.start()
            self.worker_thread = threading.Thread(
                target=self._process_messages, daemon=True
            )
            self.worker_thread.start()
            self.logger.info(
                f"Successfully connected to Redis at {REDIS_HOST}:{REDIS_PORT}"
            )
        except redis.ConnectionError as e:
            self.logger.error(
                f"Unable to connect to Redis at {REDIS_HOST}:{REDIS_PORT}.\nERROR: {str(e)}"
            )
            self.redis_client = None
            self.pubsub = None

        # Load stored tokens after logger is initialized
        self._load_stored_tokens()

    def _load_stored_tokens(self):
        """
        Loads stored tokens from secure storage on initialization.
        """
        try:
            # Load access token
            stored_access_token = keyring.get_password("flet-chat", "access_token")
            if stored_access_token:
                self.access_token = stored_access_token
                self.logger.info("Loaded stored access token")

            # Load refresh token
            stored_refresh_token = keyring.get_password("flet-chat", "refresh_token")
            if stored_refresh_token:
                self.refresh_token = stored_refresh_token
                self.logger.info("Loaded stored refresh token")

            # Load token expiry
            stored_expiry = keyring.get_password("flet-chat", "token_expiry")
            if stored_expiry:
                try:
                    self.token_expiry = datetime.fromisoformat(stored_expiry)
                    self.logger.info("Loaded stored token expiry")
                except (ValueError, TypeError):
                    self.logger.warning("Invalid stored token expiry format, ignoring")
                    self.token_expiry = None

        except Exception as e:
            self.logger.error(f"Error loading stored tokens: {str(e)}")
            # If there's an error, start with clean slate
            self.access_token = None
            self.refresh_token = None
            self.token_expiry = None

    def _store_tokens(self, access_token=None, refresh_token=None, token_expiry=None):
        """
        Securely stores tokens using the keyring library.
        """
        try:
            if access_token is not None:
                if access_token:
                    keyring.set_password("flet-chat", "access_token", access_token)
                    self.logger.info("Stored access token securely")
                else:
                    keyring.delete_password("flet-chat", "access_token")
                    self.logger.info("Removed stored access token")

            if refresh_token is not None:
                if refresh_token:
                    keyring.set_password("flet-chat", "refresh_token", refresh_token)
                    self.logger.info("Stored refresh token securely")
                else:
                    keyring.delete_password("flet-chat", "refresh_token")
                    self.logger.info("Removed stored refresh token")

            if token_expiry is not None:
                if token_expiry:
                    keyring.set_password(
                        "flet-chat", "token_expiry", token_expiry.isoformat()
                    )
                    self.logger.info("Stored token expiry securely")
                else:
                    keyring.delete_password("flet-chat", "token_expiry")
                    self.logger.info("Removed stored token expiry")

        except Exception as e:
            self.logger.error(f"Error storing tokens: {str(e)}")

    def _clear_stored_tokens(self):
        """
        Clears all stored tokens from secure storage.
        """
        try:
            keyring.delete_password("flet-chat", "access_token")
        except keyring.errors.PasswordDeleteError:
            pass  # Token doesn't exist

        try:
            keyring.delete_password("flet-chat", "refresh_token")
        except keyring.errors.PasswordDeleteError:
            pass  # Token doesn't exist

        try:
            keyring.delete_password("flet-chat", "token_expiry")
        except keyring.errors.PasswordDeleteError:
            pass  # Token doesn't exist

        self.logger.info("Cleared all stored tokens")

    def is_authenticated(self):
        """
        Checks if the user is currently authenticated with valid tokens.
        Returns True if tokens exist and appear valid, False otherwise.
        """
        if not self.access_token or not self.refresh_token:
            return False

        # Check if token is expired (with 5 minute buffer)
        if self.token_expiry:
            current_time = datetime.now(timezone.utc)
            if current_time >= self.token_expiry - timedelta(minutes=5):
                return False

        return True

    def _listen_to_pubsub(self):
        """
        Listens to Redis pubsub messages and puts them into the message queue.
        """
        while True:
            try:
                for message in self.pubsub.listen():
                    if message["type"] == "message":
                        channel = message["channel"]
                        data = message["data"]
                        self.logger.info(
                            f"Received message from Redis channel '{channel}': {data}"
                        )
                        self.message_queue.put({"channel": channel, "data": data})
            except redis.ConnectionError as e:
                self.logger.error(
                    f"Redis connection error: {str(e)}. Attempting to reconnect in 5 seconds..."
                )
                time.sleep(5)  # Wait before reconnecting
                self._reconnect_redis()
            except Exception as e:
                self.logger.error(
                    f"Unexpected error in pubsub listener: {str(e)}. Continuing..."
                )

    def _process_messages(self):
        """
        Processes messages from the message queue and invokes the appropriate callbacks.
        """
        while True:
            message = self.message_queue.get()
            channel = message["channel"]
            data = message["data"]
            if channel in self.subscriptions:
                callback = self.subscriptions[channel]
                self.logger.info(f"Processing message for channel '{channel}'")
                try:
                    callback(data)
                except Exception as e:
                    self.logger.error(
                        f"Error in callback for channel '{channel}': {str(e)}"
                    )

    def _handle_response(self, response):
        """
        Handles HTTP responses and returns an ApiResponse object.
        """
        if 200 <= response.status_code < 300:
            try:
                data = response.json() if response.content else {}
            except json.JSONDecodeError:
                data = {}
            return ApiResponse(True, data=data, status_code=response.status_code)
        return ApiResponse(False, status_code=response.status_code, error=response.text)

    def _refresh_token(self):
        """
        Refreshes the access token using the refresh token.
        """
        if not self.refresh_token:
            self.logger.warning("No refresh token available.")
            return False

        try:
            response = requests.post(
                f"{self.base_url}/auth/refresh",
                json={"refresh_token": self.refresh_token},
                timeout=2.0,
            )  # POST-request with timeout of 2s
            api_response = self._handle_response(response)

            if api_response.success:
                self.access_token = api_response.data.get("access_token")
                self.refresh_token = api_response.data.get("refresh_token")
                expires_at = api_response.data.get("expires_at")
                if expires_at:
                    self.token_expiry = datetime.fromisoformat(expires_at).replace(
                        tzinfo=pytz.UTC
                    )

                # Store new tokens securely
                self._store_tokens(
                    access_token=self.access_token,
                    refresh_token=self.refresh_token,
                    token_expiry=self.token_expiry,
                )
                self.logger.info("Token refreshed successfully.")
                return True
            else:
                self.logger.error("Failed to refresh token.")
                self.access_token = None
                self.refresh_token = None
                self.token_expiry = None
                # Clear stored tokens since refresh failed
                self._clear_stored_tokens()
                return False
        except Exception as e:
            self.logger.error(f"Exception during token refresh: {str(e)}")
            return False

    def _request(self, method, endpoint, auth_required=True, **kwargs):
        """
        Makes an HTTP request to the specified endpoint with optional authentication.
        """
        url = f"{self.base_url}{endpoint}"
        headers = kwargs.get("headers", {})

        if auth_required:
            current_time = datetime.now(timezone.utc)
            if not self.access_token or (
                self.token_expiry
                and current_time >= self.token_expiry - timedelta(minutes=5)
            ):
                if not self._refresh_token():
                    return ApiResponse(
                        False, error="Failed to refresh token. Please log in again."
                    )

            headers["Authorization"] = f"Bearer {self.access_token}"
            kwargs["headers"] = headers

        try:
            response = requests.request(method, url, **kwargs)
            api_response = self._handle_response(response)

            if (
                not api_response.success
                and api_response.status_code == 401
                and "Could not validate credentials" in (api_response.error or "")
            ):
                self.logger.warning(
                    "Received 401 Unauthorized. Attempting to refresh token."
                )
                if self._refresh_token():
                    headers["Authorization"] = f"Bearer {self.access_token}"
                    kwargs["headers"] = headers
                    response = requests.request(method, url, **kwargs)
                    api_response = self._handle_response(response)

            return api_response
        except Exception as e:
            self.logger.error(f"HTTP request exception: {str(e)}")
            return ApiResponse(False, error=str(e))

    def subscribe_to_channel(self, channel_name, callback):
        """
        Subscribes to a Redis channel with a specified callback function.
        """
        if not self.pubsub:
            self.logger.error(
                "Cannot subscribe to channel. Redis client is not connected."
            )
            return

        if channel_name not in self.subscriptions:
            self.subscriptions[channel_name] = callback
            self.pubsub.subscribe(**{channel_name: self._handle_redis_message})
            self.logger.info(f"Subscribed to Redis channel '{channel_name}'")
        else:
            self.logger.warning(f"Already subscribed to Redis channel '{channel_name}'")

    def unsubscribe_from_channel(self, channel_name):
        """
        Unsubscribes from a Redis channel.
        """
        if not self.pubsub:
            self.logger.error(
                "Cannot unsubscribe from channel. Redis client is not connected."
            )
            return

        if channel_name in self.subscriptions:
            del self.subscriptions[channel_name]
            self.pubsub.unsubscribe(channel_name)
            self.logger.info(f"Unsubscribed from Redis channel '{channel_name}'")
        else:
            self.logger.warning(f"Not subscribed to Redis channel '{channel_name}'")

    def _handle_redis_message(self, message):
        """
        Handles incoming Redis messages and delegates them to the appropriate callback.
        """
        if message["type"] == "message":
            channel = message["channel"]
            data = message["data"]
            if channel in self.subscriptions:
                self.logger.info(f"Handling message from channel '{channel}': {data}")
                try:
                    self.subscriptions[channel](data)
                except Exception as e:
                    self.logger.error(
                        f"Error in callback for channel '{channel}': {str(e)}"
                    )

    def _reconnect_redis(self):
        """
        Attempts to reconnect to Redis and resubscribe to channels.
        """
        REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
        REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
        try:
            self.redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=0,
                decode_responses=True,
                socket_connect_timeout=5,
            )
            self.redis_client.ping()
            self.pubsub = self.redis_client.pubsub()
            # Resubscribe to existing channels
            for channel in self.subscriptions.keys():
                self.pubsub.subscribe(**{channel: self._handle_redis_message})
                self.logger.info(f"Resubscribed to Redis channel '{channel}'")
            self.logger.info(f"Reconnected to Redis at {REDIS_HOST}:{REDIS_PORT}")
        except redis.ConnectionError as e:
            self.logger.error(
                f"Failed to reconnect to Redis: {str(e)}. Will retry in 5 seconds."
            )
            time.sleep(5)
            self._reconnect_redis()

    def close(self):
        """
        Closes Redis pubsub and client connections gracefully.
        """
        if self.pubsub:
            self.pubsub.close()
            self.logger.info("Closed Redis pubsub.")
        if self.redis_client:
            self.redis_client.close()
            self.logger.info("Closed Redis client.")

    def login(self, username, password):
        """
        Logs in the user by sending credentials to the server.
        """
        response = self._request(
            "POST",
            "/auth/login",
            auth_required=False,
            data={"username": username, "password": password},
        )
        if response.success:
            self.access_token = response.data.get("access_token")
            self.refresh_token = response.data.get("refresh_token")
            expires_at = response.data.get("expires_at")
            if expires_at:
                self.token_expiry = datetime.fromisoformat(expires_at).replace(
                    tzinfo=pytz.UTC
                )

            # Store tokens securely
            self._store_tokens(
                access_token=self.access_token,
                refresh_token=self.refresh_token,
                token_expiry=self.token_expiry,
            )
            self.logger.info("Logged in successfully.")
        else:
            self.logger.error(f"Login failed: {response.error}")
        return response

    def register(self, username, email, password):
        """
        Registers a new user with the provided credentials.
        """
        response = self._request(
            "POST",
            "/auth/register",
            auth_required=False,
            json={"username": username, "email": email, "password": password},
        )
        if response.success:
            self.logger.info(f"User '{username}' registered successfully.")
        else:
            self.logger.error(
                f"Registration failed for user '{username}': {response.error}"
            )
        return response

    def get_chats(self, skip=0, limit=100, name=None):
        """
        Retrieves a list of chats with optional filtering.
        """
        params = {"skip": skip, "limit": limit}
        if name:
            params["name"] = name
        return self._request("GET", "/chats/", params=params)

    def create_chat(self, chat_data):
        """
        Creates a new chat with the provided data.
        """
        response = self._request("POST", "/chats/", json=chat_data)
        if response.success:
            self.logger.info(f"Chat created successfully: {chat_data}")
        else:
            self.logger.error(f"Failed to create chat: {response.error}")
        return response

    def get_chat(self, chat_id):
        """
        Retrieves details of a specific chat by ID.
        """
        return self._request("GET", f"/chats/{chat_id}")

    def update_chat(self, chat_id, chat_data):
        """
        Updates a specific chat with the provided data.
        """
        response = self._request("PUT", f"/chats/{chat_id}", json=chat_data)
        if response.success:
            self.logger.info(f"Chat '{chat_id}' updated successfully.")
        else:
            self.logger.error(f"Failed to update chat '{chat_id}': {response.error}")
        return response

    def delete_chat(self, chat_id):
        """
        Deletes a specific chat by ID.
        """
        response = self._request("DELETE", f"/chats/{chat_id}")
        if response.success:
            self.logger.info(f"Chat '{chat_id}' deleted successfully.")
        else:
            self.logger.error(f"Failed to delete chat '{chat_id}': {response.error}")
        return response

    def add_chat_member(self, chat_id: int, user_id: int):
        """
        Adds a member to a specific chat.
        """
        response = self._request(
            "POST", f"/chats/{chat_id}/members", json={"user_id": user_id}
        )
        if response.success:
            self.logger.info(f"User '{user_id}' added to chat '{chat_id}'.")
        else:
            self.logger.error(
                f"Failed to add user '{user_id}' to chat '{chat_id}': {response.error}"
            )
        return response

    def remove_chat_member(self, chat_id, user_id):
        """
        Removes a member from a specific chat.
        """
        response = self._request("DELETE", f"/chats/{chat_id}/members/{user_id}")
        if response.success:
            self.logger.info(f"User '{user_id}' removed from chat '{chat_id}'.")
        else:
            self.logger.error(
                f"Failed to remove user '{user_id}' from chat '{chat_id}': {response.error}"
            )
        return response

    def get_messages(self, chat_id, skip=0, limit=100, content=None):
        """
        Retrieves messages from a specific chat with optional filtering.
        """
        params = {"skip": skip, "limit": limit}
        if content:
            params["content"] = content
        return self._request("GET", f"/messages/{chat_id}", params=params)

    def send_message(self, chat_id, content):
        """
        Sends a new message to a specific chat.
        """
        response = self._request(
            "POST", "/messages/", json={"chat_id": chat_id, "content": content}
        )
        if response.success:
            self.logger.info(f"Message sent to chat '{chat_id}': {content}")
        else:
            self.logger.error(
                f"Failed to send message to chat '{chat_id}': {response.error}"
            )
        return response

    def update_message(self, message_id, message_data):
        """
        Updates a specific message by ID.
        """
        response = self._request("PUT", f"/messages/{message_id}", json=message_data)
        if response.success:
            self.logger.info(f"Message '{message_id}' updated successfully.")
        else:
            self.logger.error(
                f"Failed to update message '{message_id}': {response.error}"
            )
        return response

    def delete_message(self, message_id):
        """
        Deletes a specific message by ID.
        """
        response = self._request("DELETE", f"/messages/{message_id}")
        if response.success:
            self.logger.info(f"Message '{message_id}' deleted successfully.")
        else:
            self.logger.error(
                f"Failed to delete message '{message_id}': {response.error}"
            )
        return response

    def get_current_user(self):
        """
        Retrieves the currently authenticated user's information.
        """
        return self._request("GET", "/users/me")

    def update_user(self, user_data):
        """
        Updates the current user's information.
        """
        response = self._request("PUT", "/users/me", json=user_data)
        if response.success:
            self.logger.info("User information updated successfully.")
        else:
            self.logger.error(f"Failed to update user information: {response.error}")
        return response

    def delete_user(self):
        """
        Deletes the currently authenticated user's account.
        """
        response = self._request("DELETE", "/users/me")
        if response.success:
            # Clear tokens when account is deleted
            self.access_token = None
            self.refresh_token = None
            self.token_expiry = None
            self._clear_stored_tokens()
            self.logger.info("User account deleted successfully.")
        else:
            self.logger.error(f"Failed to delete user account: {response.error}")
        return response

    def get_users(self, skip=0, limit=100, username=None):
        """
        Retrieves a list of users with optional filtering.
        """
        params = {"skip": skip, "limit": limit}
        if username:
            params["username"] = username
        return self._request("GET", "/users/", params=params)

    def search_users(self, query: str):
        """
        Searches for users based on a query string.
        """
        return self._request("GET", "/users/search", params={"query": query})

    def start_chat(self, other_user_id: int):
        """
        Initiates a new chat with another user.
        """
        response = self._request(
            "POST", "/chats/start", json={"other_user_id": other_user_id}
        )
        if response.success:
            self.logger.info(f"Started chat with user '{other_user_id}'.")
        else:
            self.logger.error(
                f"Failed to start chat with user '{other_user_id}': {response.error}"
            )
        return response

    def logout(self):
        """
        Logs out the current user by invalidating the access token.
        """
        response = self._request("POST", "/auth/logout")
        if response.success:
            self.access_token = None
            self.refresh_token = None
            self.token_expiry = None
            # Clear stored tokens on successful logout
            self._clear_stored_tokens()
            self.logger.info("Logged out successfully.")
        else:
            self.logger.error(f"Logout failed: {response.error}")
        return response

    def get_unread_messages_count(self, chat_id: int):
        """
        Retrieves the count of unread messages for a specific chat.
        """
        return self._request("GET", f"/chats/{chat_id}/unread_count")

    def update_message_status(self, message_id: int, status_update: dict):
        """
        Updates the status of a specific message.
        """
        response = self._request(
            "PUT", f"/messages/{message_id}/status", json=status_update
        )
        if response.success:
            self.logger.info(
                f"Updated status for message '{message_id}': {status_update}"
            )
        else:
            self.logger.error(
                f"Failed to update status for message '{message_id}': {response.error}"
            )
        return response
