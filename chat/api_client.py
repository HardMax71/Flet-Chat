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
        self.token = None

    def _handle_response(self, response):
        if response.status_code >= 200 and response.status_code < 300:
            if response.status_code == 204:  # No Content
                return ApiResponse(True, data={}, status_code=response.status_code)
            return ApiResponse(True, data=response.json(), status_code=response.status_code)
        else:
            return ApiResponse(False, status_code=response.status_code, error=response.text)

    def login(self, username, password):
        response = requests.post(f"{self.base_url}/auth/login", data={"username": username, "password": password})
        api_response = self._handle_response(response)
        if api_response.success:
            self.token = api_response.data["access_token"]
        return api_response

    def register(self, username, email, password):
        response = requests.post(f"{self.base_url}/auth/register", json={"username": username, "email": email, "password": password})
        return self._handle_response(response)

    def get_chats(self, skip=0, limit=100, name=None):
        headers = {"Authorization": f"Bearer {self.token}"}
        params = {"skip": skip, "limit": limit}
        if name:
            params["name"] = name
        response = requests.get(f"{self.base_url}/chats/", headers=headers, params=params)
        return self._handle_response(response)

    def create_chat(self, chat_data):
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.post(f"{self.base_url}/chats/", headers=headers, json=chat_data)
        return self._handle_response(response)

    def get_chat(self, chat_id):
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(f"{self.base_url}/chats/{chat_id}", headers=headers)
        return self._handle_response(response)

    def update_chat(self, chat_id, chat_data):
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.put(f"{self.base_url}/chats/{chat_id}", headers=headers, json=chat_data)
        return self._handle_response(response)

    def delete_chat(self, chat_id):
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.delete(f"{self.base_url}/chats/{chat_id}", headers=headers)
        return self._handle_response(response)

    def add_chat_member(self, chat_id: int, user_id: int):
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.post(f"{self.base_url}/chats/{chat_id}/members", headers=headers, json={"user_id": user_id})
        return self._handle_response(response)

    def remove_chat_member(self, chat_id, user_id):
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.delete(f"{self.base_url}/chats/{chat_id}/members/{user_id}", headers=headers)
        return self._handle_response(response)

    def get_messages(self, chat_id, skip=0, limit=100, content=None):
        headers = {"Authorization": f"Bearer {self.token}"}
        params = {"skip": skip, "limit": limit}
        if content:
            params["content"] = content
        response = requests.get(f"{self.base_url}/messages/{chat_id}", headers=headers, params=params)
        return self._handle_response(response)

    def send_message(self, chat_id, content):
        headers = {"Authorization": f"Bearer {self.token}"}
        data = {"chat_id": chat_id, "content": content}
        response = requests.post(f"{self.base_url}/messages/", headers=headers, json=data)
        return self._handle_response(response)

    def update_message(self, message_id, message_data):
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.put(f"{self.base_url}/messages/{message_id}", headers=headers, json=message_data)
        return self._handle_response(response)

    def delete_message(self, message_id):
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.delete(f"{self.base_url}/messages/{message_id}", headers=headers)
        return self._handle_response(response)

    def get_current_user(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(f"{self.base_url}/users/me", headers=headers)
        return self._handle_response(response)

    def update_user(self, user_data):
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.put(f"{self.base_url}/users/me", headers=headers, json=user_data)
        return self._handle_response(response)

    def delete_user(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.delete(f"{self.base_url}/users/me", headers=headers)
        return self._handle_response(response)

    def get_users(self, skip=0, limit=100, username=None):
        headers = {"Authorization": f"Bearer {self.token}"}
        params = {"skip": skip, "limit": limit}
        if username:
            params["username"] = username
        response = requests.get(f"{self.base_url}/users/", headers=headers, params=params)
        return self._handle_response(response)

    def search_users(self, query: str):
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(f"{self.base_url}/users/search", headers=headers, params={"query": query})
        return self._handle_response(response)

    def start_chat(self, other_user_id: int):
        headers = {"Authorization": f"Bearer {self.token}"}
        params = {"other_user_id": other_user_id}
        response = requests.post(f"{self.base_url}/chats/start", headers=headers, params=params)
        return self._handle_response(response)