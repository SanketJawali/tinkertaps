from httpx import AsyncClient


async def test_unknown_route_returns_structured_error_response(client: AsyncClient):
    response = await client.get("/this-route-does-not-exist")

    assert response.status_code == 404
    body = response.json()
    assert body["detail"] == "Not Found"
    assert body["request_id"] is not None
