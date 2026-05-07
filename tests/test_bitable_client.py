from unittest.mock import MagicMock

import pytest

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
    sent_records = []
    for call in post.call_args_list:
        body = call.kwargs["json"]["records"]
        sent_records.extend(body)
    assert len(sent_records) == 1200
    chunk_sizes = [len(call.kwargs["json"]["records"]) for call in post.call_args_list]
    assert chunk_sizes == [500, 500, 200]


def test_batch_delete_chunks_record_ids(mocker):
    mocker.patch.object(BitableClient, "_get_tenant_access_token", return_value="t")
    post = mocker.patch(
        "scripts.bitable_client.requests.post",
        return_value=_resp({"code": 0}),
    )
    client = BitableClient("app", "secret", "base")
    ids = [f"r{i}" for i in range(1100)]
    client.batch_delete("tbl", ids)

    assert post.call_count == 3
    sent_ids = []
    for call in post.call_args_list:
        sent_ids.extend(call.kwargs["json"]["records"])
    assert sent_ids == ids
    chunk_sizes = [len(call.kwargs["json"]["records"]) for call in post.call_args_list]
    assert chunk_sizes == [500, 500, 100]


def test_update_record_calls_put(mocker):
    mocker.patch.object(BitableClient, "_get_tenant_access_token", return_value="t")
    put = mocker.patch(
        "scripts.bitable_client.requests.put",
        return_value=_resp({"code": 0}),
    )
    client = BitableClient("app", "secret", "base")
    client.update_record("tbl", "rec1", {"a": 1})
    assert put.call_count == 1


def test_list_records_raises_on_non_zero_code(mocker):
    mocker.patch.object(BitableClient, "_get_tenant_access_token", return_value="t")
    mocker.patch(
        "scripts.bitable_client.requests.get",
        return_value=_resp({"code": 99999, "msg": "boom", "data": {}}),
    )
    client = BitableClient("app", "secret", "base")
    with pytest.raises(RuntimeError, match="Feishu list_records error"):
        client.list_records("tbl")


def test_get_tenant_access_token_caches_within_validity_window(mocker):
    post = mocker.patch(
        "scripts.bitable_client.requests.post",
        return_value=_resp(
            {"code": 0, "tenant_access_token": "t-cached", "expire": 7200}
        ),
    )
    client = BitableClient("app", "secret", "base")
    first = client._get_tenant_access_token()
    second = client._get_tenant_access_token()
    assert first == second == "t-cached"
    assert post.call_count == 1
