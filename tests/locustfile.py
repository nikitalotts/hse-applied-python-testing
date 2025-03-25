import uuid
import random
from locust import HttpUser, task, between


class RegisteredUser(HttpUser):
    wait_time = between(1, 3)
    host = "http://localhost:8000"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cookies = {}
        self.short_codes = []
        self.urls_for_search = {}
        self.user_email = f"user_{uuid.uuid4().hex[:10]}@example.com"
        self.user_password = "password"

    def on_start(self):
        register_response = self.client.post(
            "/auth/register",
            json={
                "email": self.user_email,
                "password": self.user_password
            }
        )

        if register_response.status_code not in [200, 201]:
            self.environment.runner.quit()
            return

        auth_response = self.client.post(
            "/auth/jwt/login",
            data={
                "grant_type": "password",
                "username": self.user_email,
                "password": self.user_password,
                "client_id": "string",
                "client_secret": "string"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        if auth_response.status_code == 204:
            self.cookies = auth_response.cookies.get_dict()
        else:
            self.environment.runner.quit()

        # Создаем первую ссылку для тестов
        link = f"http://google.com/search?q={uuid.uuid4()}"
        alias = uuid.uuid4().hex[:16]
        data = {
            "original_url": link,
            "custom_alias": f"{alias}",
            "expires_at": "2026-01-01T00:00:00"
        }
        response = self.client.post(
            "/links/shorten",
            json=data,
            cookies=self.cookies,
            allow_redirects=False
        )
        if response.ok:
            self.urls_for_search[alias] = link
            self.short_codes.append(alias)

    @task(16)
    def redirect_link(self):
        if self.short_codes:
            link = f"/links/{random.choice(self.short_codes)}"
            self.client.get(
                link,
                name="/links/[short_code]",
                cookies=self.cookies,
                allow_redirects=False,
                # catch_response=True
            )

    @task(8)
    def create_short_link(self):
        new_url = f"http://google.com/search?q={uuid.uuid4()}"
        data = {
            "original_url": new_url,
            "custom_alias": f"{uuid.uuid4().hex[:16]}",
            "expires_at": "2026-01-01T00:00:00"
        }
        response = self.client.post(
            "/links/shorten",
            json=data,
            cookies=self.cookies
        )
        if response.ok:
            short_code = response.json()["link"].split("/")[-1]
            self.short_codes.append(short_code)
            self.urls_for_search[short_code] = new_url

    @task(4)
    def update(self):
        if self.short_codes:
            short_code = random.choice(self.short_codes)
            new_url = f"http://google.com/search?q={uuid.uuid4()}"
            _ = self.client.put(
                f"/links/{short_code}",
                json={
                    "original_url": new_url,
                    "expires_at": "2026-01-01T00:00:00"
                },
                name="/links/[short_code]",
                cookies=self.cookies,
                verify=False
            )
            self.urls_for_search[short_code] = new_url

    @task(4)
    def delete(self):
        if self.short_codes:
            short_code = random.choice(self.short_codes)
            delete_response = self.client.delete(
                f"/links/{short_code}",
                name="/links/[short_code]",
                cookies=self.cookies,
                verify=False
            )
            if delete_response.ok:
                self.short_codes.remove(short_code)
                del self.urls_for_search[short_code]

    @task(2)
    def get_stats(self):
        if self.short_codes:
            short_code = random.choice(self.short_codes)
            self.client.get(
                f"/links/{short_code}/stats",
                name="/links/[short_code]/stats",
                cookies=self.cookies,
                verify=False
            )

    @task(2)
    def get_all(self):
        self.client.get(
            "/links/all",
            name="/links/all",
            cookies=self.cookies,
            verify=False
        )

    @task(1)
    def search(self):
        if self.urls_for_search:
            url_to_search = random.choice(list(self.urls_for_search.values()))
            self.client.get(
                "/links/search",
                name="/links/search",
                params={"original_url": url_to_search},
                cookies=self.cookies,
                verify=False
            )

    @task(1)
    def export(self):
        self.client.get(
            "/links/my-statistics",
            cookies=self.cookies,
            verify=False
        )

    @task(1)
    def health(self):
        self.client.get(
            "/health",
            verify=False
        )
