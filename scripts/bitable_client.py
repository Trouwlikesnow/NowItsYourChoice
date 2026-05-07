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

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._get_tenant_access_token()}"}

    def list_records(
        self, table_id: str, page_size: int = 500, filter_: str | None = None
    ) -> list[dict]:
        url = (
            f"{self.BASE_URL}/bitable/v1/apps/{self.base_app_token}"
            f"/tables/{table_id}/records"
        )
        page_token: str | None = None
        out: list[dict] = []
        while True:
            params: dict = {"page_size": page_size}
            if page_token:
                params["page_token"] = page_token
            if filter_:
                params["filter"] = filter_
            resp = requests.get(url, headers=self._headers(), params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                raise RuntimeError(f"Feishu list_records error: {data}")
            payload = data.get("data", {})
            out.extend(payload.get("items", []))
            if not payload.get("has_more"):
                break
            page_token = payload.get("page_token")
        return out
