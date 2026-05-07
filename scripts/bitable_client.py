import time

import requests


class BitableClient:
    BASE_URL = "https://open.feishu.cn/open-apis"

    def __init__(self, app_id: str, app_secret: str, base_app_token: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.base_app_token = base_app_token
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    def _get_tenant_access_token(self) -> str:
        now = time.time()
        if self._token and now < self._token_expires_at - 60:
            return self._token
        resp = requests.post(
            f"{self.BASE_URL}/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"Feishu token error: {data}")
        self._token = data["tenant_access_token"]
        self._token_expires_at = now + data.get("expire", 7200)
        return self._token
