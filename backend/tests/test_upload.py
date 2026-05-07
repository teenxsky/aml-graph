import pytest
from httpx import AsyncClient


async def test_upload_returns_session_id(
    client: AsyncClient,
    sample_csv: bytes,
    column_mapping_json: str,
) -> None:
    response = await client.post(
        '/api/v1/upload',
        files={'file': ('test.csv', sample_csv, 'text/csv')},
        data={'column_mapping': column_mapping_json},
    )
    assert response.status_code == 200
    body = response.json()
    assert 'session_id' in body
    assert isinstance(body['session_id'], str)
    assert len(body['session_id']) == 36  # UUID4


async def test_upload_empty_file(client: AsyncClient, column_mapping_json: str) -> None:
    response = await client.post(
        '/api/v1/upload',
        files={'file': ('test.csv', b'', 'text/csv')},
        data={'column_mapping': column_mapping_json},
    )
    assert response.status_code == 400


async def test_upload_invalid_mapping_json(client: AsyncClient, sample_csv: bytes) -> None:
    response = await client.post(
        '/api/v1/upload',
        files={'file': ('test.csv', sample_csv, 'text/csv')},
        data={'column_mapping': 'not-valid-json'},
    )
    assert response.status_code == 422


async def test_upload_missing_required_mapping_field(
    client: AsyncClient,
    sample_csv: bytes,
) -> None:
    import json

    mapping = json.dumps({'sender_id': 'sender', 'receiver_id': 'receiver'})
    response = await client.post(
        '/api/v1/upload',
        files={'file': ('test.csv', sample_csv, 'text/csv')},
        data={'column_mapping': mapping},
    )
    assert response.status_code == 422


async def test_upload_with_device_id(client: AsyncClient, column_mapping_json: str) -> None:
    import csv
    import io
    import json

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=['sender', 'receiver', 'amount', 'ts', 'dev'])
    writer.writeheader()
    writer.writerows([
        {'sender': 'C001', 'receiver': 'A001', 'amount': '500', 'ts': '2024-01-01T00:00:00', 'dev': 'DEV_X'},
        {'sender': 'C002', 'receiver': 'A001', 'amount': '500', 'ts': '2024-01-01T01:00:00', 'dev': 'DEV_X'},
    ])
    csv_bytes = buf.getvalue().encode()
    mapping = json.dumps({
        'sender_id': 'sender',
        'receiver_id': 'receiver',
        'amount': 'amount',
        'timestamp': 'ts',
        'device_id': 'dev',
    })

    response = await client.post(
        '/api/v1/upload',
        files={'file': ('test.csv', csv_bytes, 'text/csv')},
        data={'column_mapping': mapping},
    )
    assert response.status_code == 200
    assert 'session_id' in response.json()
