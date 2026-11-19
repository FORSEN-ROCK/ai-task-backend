import asyncio
import json

from starlette.types import Message

from app.main import app


def test_health_returns_ok() -> None:
    messages: list[Message] = []

    async def receive() -> Message:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Message) -> None:
        messages.append(message)

    asyncio.run(
        app(
            {
                "type": "http",
                "method": "GET",
                "path": "/health",
                "headers": [],
                "query_string": b"",
            },
            receive,
            send,
        )
    )

    response_start, response_body = messages
    assert response_start["status"] == 200
    assert json.loads(response_body["body"]) == {"status": "ok"}
