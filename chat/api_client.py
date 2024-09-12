from datetime import datetime, timedelta
import pytz
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

    def _handle_response(self, response):
        if 200 <= response.status_code < 300:
            return ApiResponse(True, data=response.json() if response.content else {}, status_code=response.status_code)
        return ApiResponse(False, status_code=response.status_code, error=response.text)

    def _refresh_token(self):
        if not self.refresh_token:
            return False

        response = requests.post(f"{self.base_url}/auth/refresh", json={"refresh_token": self.refresh_token})
        api_response = self._handle_response(response)

        if api_response.success:
            self.access_token = api_response.data["access_token"]
            self.refresh_token = api_response.data["refresh_token"]
            self.token_expiry = datetime.fromisoformat(api_response.data["expires_at"])
            return True
        else:
            self.access_token = None
            self.refresh_token = None
            self.token_expiry = None
            return False

    def _request(self, method, endpoint, auth_required=True, **kwargs):
        url = f"{self.base_url}{endpoint}"

        if auth_required:
            current_time = datetime.utcnow().replace(tzinfo=pytz.UTC)
            if not self.access_token or (
                    self.token_expiry and current_time >= self.token_expiry - timedelta(minutes=5)):
                if not self._refresh_token():
                    return ApiResponse(False, error="Failed to refresh token. Please log in again.")

            headers = kwargs.get('headers', {})
            headers['Authorization'] = f"Bearer {self.access_token}"
            kwargs['headers'] = headers

        response = requests.request(method, url, **kwargs)
        api_response = self._handle_response(response)

        if not api_response.success and api_response.status_code == 401 and "Could not validate credentials" in api_response.error:
            if self._refresh_token():
                # Retry the request with the new token
                kwargs['headers']['Authorization'] = f"Bearer {self.access_token}"
                response = requests.request(method, url, **kwargs)
                api_response = self._handle_response(response)

        return api_response

    def login(self, username, password):
        response = self._request("POST", "/auth/login", auth_required=False,
                                 data={"username": username, "password": password})
        if response.success:
            self.access_token = response.data["access_token"]
            self.refresh_token = response.data["refresh_token"]
            self.token_expiry = datetime.fromisoformat(response.data["expires_at"]).replace(tzinfo=pytz.UTC)
        return response

    def register(self, username, email, password):
        return self._request("POST", "/auth/register", auth_required=False,
                             json={"username": username, "email": email, "password": password})

    def get_chats(self, skip=0, limit=100, name=None):
        params = {"skip": skip, "limit": limit}
        if name:
            params["name"] = name
        return self._request("GET", "/chats/", params=params)

    def create_chat(self, chat_data):
        return self._request("POST", "/chats/", json=chat_data)

    def get_chat(self, chat_id):
        return self._request("GET", f"/chats/{chat_id}")

    def update_chat(self, chat_id, chat_data):
        return self._request("PUT", f"/chats/{chat_id}", json=chat_data)

    def delete_chat(self, chat_id):
        return self._request("DELETE", f"/chats/{chat_id}")

    def add_chat_member(self, chat_id: int, user_id: int):
        return self._request("POST", f"/chats/{chat_id}/members", json={"user_id": user_id})

    def remove_chat_member(self, chat_id, user_id):
        return self._request("DELETE", f"/chats/{chat_id}/members/{user_id}")

    def get_messages(self, chat_id, skip=0, limit=100, content=None):
        params = {"skip": skip, "limit": limit}
        if content:
            params["content"] = content
        return self._request("GET", f"/messages/{chat_id}", params=params)

    def send_message(self, chat_id, content):
        return self._request("POST", "/messages/", json={"chat_id": chat_id, "content": content})

    def update_message(self, message_id, message_data):
        return self._request("PUT", f"/messages/{message_id}", json=message_data)

    def delete_message(self, message_id):
        return self._request("DELETE", f"/messages/{message_id}")

    def get_current_user(self):
        return self._request("GET", "/users/me")

    def update_user(self, user_data):
        return self._request("PUT", "/users/me", json=user_data)

    def delete_user(self):
        return self._request("DELETE", "/users/me")

    def get_users(self, skip=0, limit=100, username=None):
        params = {"skip": skip, "limit": limit}
        if username:
            params["username"] = username
        return self._request("GET", "/users/", params=params)

    def search_users(self, query: str):
        return self._request("GET", "/users/search", params={"query": query})

    def start_chat(self, other_user_id: int):
        return self._request("POST", "/chats/start", json={"other_user_id": other_user_id})

    def logout(self):
        response = self._request("POST", "/auth/logout")
        if response.success:
            self.access_token = None
            self.refresh_token = None
            self.token_expiry = None
        return response

    def get_unread_messages_count(self, chat_id: int):
        return self._request("GET", f"/chats/{chat_id}/unread_count")

    def update_message_status(self, message_id: int, status_update: dict):
        return self._request("PUT", f"/messages/{message_id}/status", json=status_update)