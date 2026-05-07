from unittest.mock import MagicMock, patch

from scripts.bitable_client import BitableClient


def _resp(payload):
    r = MagicMock()
    r.json.return_value = payload
    r.raise_for_status.return_value = None
    return r


def test_get_tenant_access_token_returns_token(mocker):
    mocker.patch(
        "scripts.bitable_client.requests.post",
        return_value=_resp(
            {"code": 0, "tenant_access_token": "t-fake-token", "expire": 7200}
        ),
    )
    client = BitableClient("app", "secret", "base")
    assert client._get_tenant_access_token() == "t-fake-token"
