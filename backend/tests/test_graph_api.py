from httpx import AsyncClient


async def test_graph_api_stats_graph_alerts_filters(client: AsyncClient, ibm_csv: bytes) -> None:
    upload = await client.post(
        '/api/v1/upload/ibm',
        files={'file': ('ibm.csv', ibm_csv, 'text/csv')},
    )
    session_id = upload.json()['session_id']

    stats = await client.get(f'/api/v1/sessions/{session_id}/stats')
    graph = await client.get(f'/api/v1/sessions/{session_id}/graph')
    alerts = await client.get(f'/api/v1/sessions/{session_id}/alerts')
    filters = await client.get(f'/api/v1/sessions/{session_id}/filters')

    assert stats.status_code == 200
    assert stats.json()['node_count'] == 3
    assert stats.json()['edge_count'] == 2
    assert stats.json()['laundering_label_count'] == 1
    assert graph.status_code == 200
    assert graph.json()['nodes'][0]['id']
    assert graph.json()['edges'][0]['source']
    assert alerts.status_code == 200
    assert 'alerts' in alerts.json()
    assert filters.status_code == 200
    assert 'payment_formats' in filters.json()


async def test_graph_api_subgraph(client: AsyncClient, ibm_csv: bytes) -> None:
    upload = await client.post(
        '/api/v1/upload/ibm',
        files={'file': ('ibm.csv', ibm_csv, 'text/csv')},
    )
    session_id = upload.json()['session_id']

    response = await client.get(f'/api/v1/sessions/{session_id}/subgraph?node_id=B2:A2&k=1')

    assert response.status_code == 200
    assert response.json()['nodes']
