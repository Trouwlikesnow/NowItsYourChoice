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


def test_list_records_returns_items_across_pages(mocker):
    mocker.patch.object(BitableClient, "_get_tenant_access_token", return_value="t")
    get = mocker.patch(
        "scripts.bitable_client.requests.get",
        side_effect=[
            _resp(
                {
                    "code": 0,
                    "data": {
                        "items": [{"record_id": "r1", "fields": {"代码": "002594"}}],
                        "has_more": True,
                        "page_token": "tok1",
                    },
                }
            ),
            _resp(
                {
                    "code": 0,
                    "data": {
                        "items": [{"record_id": "r2", "fields": {"代码": "300750"}}],
                        "has_more": False,
                    },
                }
            ),
        ],
    )
    client = BitableClient("app", "secret", "base")
    records = client.list_records("tbl")
    assert len(records) == 2
    assert records[0]["record_id"] == "r1"
    assert records[1]["record_id"] == "r2"
    assert get.call_count == 2


def test_batch_create_chunks_and_calls_api(mocker):
    mocker.patch.object(BitableClient, "_get_tenant_access_token", return_value="t")
    post = mocker.patch(
        "scripts.bitable_client.requests.post",
        return_value=_resp({"code": 0, "data": {"records": []}}),
    )
    client = BitableClient("app", "secret", "base")
    records = [{"代码": str(i)} for i in range(1200)]
    client.batch_create("tbl", records)
    assert post.call_count == 3
