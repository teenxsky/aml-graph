from httpx import AsyncClient


async def test_upload_valid_ibm_csv_returns_session_id(client: AsyncClient, ibm_csv: bytes) -> None:
    response = await client.post(
        '/api/v1/upload/ibm',
        files={'file': ('ibm.csv', ibm_csv, 'text/csv')},
    )

    assert response.status_code == 200
    assert len(response.json()['session_id']) == 36


async def test_upload_ibm_missing_column_returns_422(client: AsyncClient, ibm_rows: list[dict]) -> None:
    import csv
    import io

    rows = [{k: v for k, v in row.items() if k != 'Amount Paid'} for row in ibm_rows]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

    response = await client.post(
        '/api/v1/upload/ibm',
        files={'file': ('ibm.csv', buf.getvalue().encode(), 'text/csv')},
    )

    assert response.status_code == 422


async def test_upload_ibm_invalid_amount_returns_422(client: AsyncClient, ibm_rows: list[dict]) -> None:
    import csv
    import io

    ibm_rows[0]['Amount Paid'] = 'bad'
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(ibm_rows[0].keys()))
    writer.writeheader()
    writer.writerows(ibm_rows)

    response = await client.post(
        '/api/v1/upload/ibm',
        files={'file': ('ibm.csv', buf.getvalue().encode(), 'text/csv')},
    )

    assert response.status_code == 422
