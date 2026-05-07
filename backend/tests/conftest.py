import csv
import io
import json

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


def make_csv_bytes(rows: list[dict]) -> bytes:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode()


@pytest.fixture
def sample_csv() -> bytes:
    return make_csv_bytes([
        {'sender': 'C001', 'receiver': 'A001', 'amount': '1000.0', 'ts': '2024-01-01T00:00:00'},
        {'sender': 'A001', 'receiver': 'C002', 'amount': '900.0', 'ts': '2024-01-01T01:00:00'},
        {'sender': 'C002', 'receiver': 'C001', 'amount': '800.0', 'ts': '2024-01-01T02:00:00'},
    ])


@pytest.fixture
def column_mapping_json() -> str:
    return json.dumps({
        'sender_id': 'sender',
        'receiver_id': 'receiver',
        'amount': 'amount',
        'timestamp': 'ts',
    })


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as c:
        yield c


@pytest.fixture
async def session_id(client: AsyncClient, sample_csv: bytes, column_mapping_json: str) -> str:
    response = await client.post(
        '/api/v1/upload',
        files={'file': ('test.csv', sample_csv, 'text/csv')},
        data={'column_mapping': column_mapping_json},
    )
    return response.json()['session_id']
