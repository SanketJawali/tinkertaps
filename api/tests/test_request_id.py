import uuid

from httpx import AsyncClient

from app.middleware.request_id import REQUEST_ID_HEADER


async def test_adds_request_id_when_header_is_missing(client: AsyncClient):
    # Use a route that does not touch the database; we only care about headers.
    response = await client.get("/this-route-does-not-exist")

    request_id = response.headers[REQUEST_ID_HEADER]
    uuid.UUID(request_id)


async def test_preserves_request_id_when_header_is_provided(client: AsyncClient):
    existing_request_id = "550e8400-e29b-41d4-a716-446655440000"

    response = await client.get(
        "/this-route-does-not-exist",
        headers={REQUEST_ID_HEADER: existing_request_id},
    )

    assert response.headers[REQUEST_ID_HEADER] == existing_request_id
