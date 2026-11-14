from functools import lru_cache
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.routers import chat as chat_router
from backend.app.schemas.ai import TutorCompletion
from backend.app.services.embeddings import EmbeddingService


def _register(client: TestClient) -> str:
    email = f"{uuid4().hex}@example.com"
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Grace Hopper",
            "email": email,
            "password": "correct horse battery staple",
        },
    )
    assert response.status_code == 201
    login = client.post(
        "/auth/login",
        json={"email": email, "password": "correct horse battery staple"},
    )
    return login.json()["access_token"]


class FakeGroqService:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def generate_tutor_response(self, **kwargs: object) -> TutorCompletion:
        self.calls.append(kwargs)
        return TutorCompletion(
            answer="Use a loop invariant to reason about this algorithm.",
            suggested_actions=["Try a small input", "Compare the time complexity"],
        )


def test_chat_persists_contextual_tutoring_response_and_history() -> None:
    fake_service = FakeGroqService()
    original = chat_router.get_groq_service
    chat_router.get_groq_service = lambda: fake_service
    try:
        with TestClient(app) as client:
            token = _register(client)
            headers = {"Authorization": f"Bearer {token}"}
            session = client.post(
                "/chat/sessions",
                headers=headers,
                json={"title": "Algorithms help"},
            )
            response = client.post(
                f"/chat/sessions/{session.json()['id']}/messages",
                headers=headers,
                json={"message": "Explain loop invariants", "mode": "concept"},
            )
            messages = client.get(
                f"/chat/sessions/{session.json()['id']}/messages",
                headers=headers,
            )
    finally:
        chat_router.get_groq_service = original

    assert session.status_code == 201
    assert response.status_code == 200
    assert response.json()["answer"].startswith("Use a loop")
    assert [item["role"] for item in messages.json()] == ["user", "assistant"]
    assert fake_service.calls[0]["context"] == []


def test_chat_session_is_not_accessible_to_another_student() -> None:
    with TestClient(app) as client:
        first_token = _register(client)
        second_token = _register(client)
        session = client.post(
            "/chat/sessions",
            headers={"Authorization": f"Bearer {first_token}"},
            json={},
        )
        response = client.get(
            f"/chat/sessions/{session.json()['id']}/messages",
            headers={"Authorization": f"Bearer {second_token}"},
        )

    assert response.status_code == 404


def test_embedding_model_is_loaded_lazily_and_reused(monkeypatch) -> None:
    class FakeEmbedding:
        def encode(self, value: object, normalize_embeddings: bool) -> object:
            assert normalize_embeddings is True
            return _Vector([0.1, 0.2])

    class _Vector:
        def __init__(self, values: list[float]) -> None:
            self.values = values

        def tolist(self) -> list[float]:
            return self.values

    calls: list[str] = []

    @lru_cache(maxsize=2)
    def fake_loader(name: str) -> FakeEmbedding:
        calls.append(name)
        return FakeEmbedding()

    monkeypatch.setattr(
        "backend.app.services.embeddings._load_embedding_model",
        fake_loader,
    )
    service = EmbeddingService("test-model")

    assert service.embed_text("hello") == [0.1, 0.2]
    assert service.embed_text("world") == [0.1, 0.2]
    assert calls == ["test-model"]


def test_groq_service_requires_configuration() -> None:
    from backend.app.core.config import Settings
    from backend.app.services.groq_ai import AIConfigurationError, GroqAIService

    try:
        GroqAIService(
            settings=Settings(
                jwt_secret_key="x" * 32,
                groq_api_key="",
                groq_model="",
            )
        )
    except AIConfigurationError:
        pass
    else:
        raise AssertionError("Expected missing Groq configuration to fail")


def test_groq_service_validates_structured_provider_response() -> None:
    from backend.app.core.config import Settings
    from backend.app.services.groq_ai import GroqAIService

    class Message:
        content = '{"answer":"Start with the invariant.","suggested_actions":["Write it down"]}'

    class Completion:
        choices = [type("Choice", (), {"message": Message()})()]

    class Completions:
        def create(self, **kwargs: object) -> Completion:
            assert kwargs["model"] == "test-model"
            assert "Student learning context" in kwargs["messages"][0]["content"]
            return Completion()

    client = type(
        "Client",
        (),
        {"chat": type("Chat", (), {"completions": Completions()})()},
    )()
    service = GroqAIService(
        client=client,
        settings=Settings(
            jwt_secret_key="x" * 32,
            groq_api_key="test-key",
            groq_model="test-model",
        ),
    )

    result = service.generate_tutor_response(
        student_id=999999,
        mode="hint",
        message="Help",
        context=[{"topic_id": 1, "mastery_level": "Developing"}],
        history=[],
    )

    assert result.answer == "Start with the invariant."
