from httpx import AsyncClient


async def test_stream_unknown_session(client: AsyncClient) -> None:
    response = await client.get('/api/v1/stream/00000000-0000-0000-0000-000000000000')
    assert response.status_code == 404


async def test_stream_content_type(client: AsyncClient, session_id: str) -> None:
    response = await client.get(f'/api/v1/stream/{session_id}')
    assert response.status_code == 200
    assert 'text/event-stream' in response.headers['content-type']


async def test_stream_contains_all_events(client: AsyncClient, session_id: str) -> None:
    response = await client.get(f'/api/v1/stream/{session_id}')
    content = response.text

    expected_events = [
        'event: graph_meta',
        'event: nodes_chunk',
        'event: edges_chunk',
        'event: layout_done',
        'event: detector_result',
        'event: stream_done',
    ]
    for event in expected_events:
        assert event in content, f'Отсутствует {event!r} в SSE-потоке'


async def test_stream_graph_meta_fields(client: AsyncClient, session_id: str) -> None:
    import json

    response = await client.get(f'/api/v1/stream/{session_id}')
    lines = response.text.splitlines()

    meta_data: dict | None = None
    for i, line in enumerate(lines):
        if line == 'event: graph_meta' and i + 1 < len(lines):
            meta_data = json.loads(lines[i + 1].removeprefix('data: '))
            break

    assert meta_data is not None
    assert meta_data['session_id'] == session_id
    assert meta_data['node_count'] == 3
    assert meta_data['edge_count'] == 3


async def test_stream_detector_results_all_patterns(client: AsyncClient, session_id: str) -> None:
    import json

    response = await client.get(f'/api/v1/stream/{session_id}')
    lines = response.text.splitlines()

    pattern_types: set[str] = set()
    for i, line in enumerate(lines):
        if line == 'event: detector_result' and i + 1 < len(lines):
            data = json.loads(lines[i + 1].removeprefix('data: '))
            pattern_types.add(data['pattern_type'])

    assert pattern_types == {'cycles', 'fanout', 'transit', 'shared_device'}


async def test_stream_contains_completed_stage(client: AsyncClient, session_id: str) -> None:
    response = await client.get(f'/api/v1/stream/{session_id}')
    assert 'event: completed' in response.text
