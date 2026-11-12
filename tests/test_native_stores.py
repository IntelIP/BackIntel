import json

import pytest

from backintel.stores.base import QueryRefused
from backintel.stores.clickhouse import screen_sql
from backintel.stores.ferretdb import screen_query


def test_native_store_guards_accept_reads_and_reject_writes_and_external_reads():
    assert screen_sql("SELECT count() FROM orders")
    for query in (
        "DROP TABLE orders",
        "SELECT * FROM url('https://example.com')",
        "SELECT * FROM file('/etc/passwd')",
        "SELECT 1 SETTINGS readonly=0",
    ):
        with pytest.raises(QueryRefused):
            screen_sql(query)
    assert screen_query('{"collection":"orders","pipeline":[{"$count":"n"}]}') == (
        "orders",
        [{"$count": "n"}],
    )
    for pipeline in (
        [{"$out": "other"}],
        [{"$facet": {"bad": [{"$merge": "other"}]}}],
        [{"$match": {"$where": "true"}}],
    ):
        with pytest.raises(QueryRefused):
            screen_query(json.dumps({"collection": "orders", "pipeline": pipeline}))
