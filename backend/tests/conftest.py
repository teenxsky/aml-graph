import csv
import io
import json

import pytest
import pandas as pd
from httpx import ASGITransport, AsyncClient

from src.app import app


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
def ibm_rows() -> list[dict]:
    return [
        {
            'Timestamp': '2024-01-01T00:00:00',
            'From Bank': 'B1',
            'Account': 'A1',
            'To Bank': 'B2',
            'Account.1': 'A2',
            'Amount Received': '990.0',
            'Receiving Currency': 'USD',
            'Amount Paid': '1000.0',
            'Payment Currency': 'USD',
            'Payment Format': 'ACH',
            'Is Laundering': '1',
        },
        {
            'Timestamp': '2024-01-01T01:00:00',
            'From Bank': 'B2',
            'Account': 'A2',
            'To Bank': 'B3',
            'Account.1': 'A3',
            'Amount Received': '980.0',
            'Receiving Currency': 'USD',
            'Amount Paid': '990.0',
            'Payment Currency': 'USD',
            'Payment Format': 'Wire',
            'Is Laundering': '0',
        },
    ]


@pytest.fixture
def ibm_df(ibm_rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(ibm_rows)


@pytest.fixture
def ibm_csv(ibm_rows: list[dict]) -> bytes:
    return make_csv_bytes(ibm_rows)


@pytest.fixture
def column_mapping_json() -> str:
    return json.dumps({
        'sender_id': 'sender',
        'receiver_id': 'receiver',
        'amount_paid': 'amount',
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
