"""Lightweight smoke tests for the new chat routers.

The end-to-end behaviour of these routes is already covered by the
persistence-helper tests. This module just asserts the routers expose
the expected paths and methods so a refactor that breaks the URL
contract will fail loudly.
"""
from app.api.v1.chat import router as chat_router
from app.api.v1.chats import router as messages_router


def test_chat_router_exposes_only_ask_endpoint():
    paths = sorted({route.path for route in chat_router.routes})
    assert paths == ["/ask"]


def test_chat_router_uses_post_method():
    methods = set()
    for route in chat_router.routes:
        if route.methods:
            methods.update(route.methods)
    assert methods == {"POST"}


def test_messages_router_exposes_expected_paths():
    paths = sorted({route.path for route in messages_router.routes})
    assert paths == [
        "/chats",
        "/chats/{chat_id}",
        "/chats/{chat_id}/documents",
        "/chats/{chat_id}/messages",
        "/chats/{chat_id}/outline",
    ]


def test_messages_router_delete_methods():
    methods_per_path: dict[str, set[str]] = {}
    for route in messages_router.routes:
        for method in route.methods or set():
            methods_per_path.setdefault(route.path, set()).add(method)
    assert methods_per_path["/chats"] == {"GET"}
    assert methods_per_path["/chats/{chat_id}/messages"] == {"GET", "DELETE"}
    assert methods_per_path["/chats/{chat_id}/outline"] == {"GET"}
    assert methods_per_path["/chats/{chat_id}"] == {"DELETE"}
    assert methods_per_path["/chats/{chat_id}/documents"] == {"DELETE"}
