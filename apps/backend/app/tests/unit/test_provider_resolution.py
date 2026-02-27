from types import SimpleNamespace

from app.services.provider_service import ProviderService


class DummySettingsService:
    def __init__(self, model_mappings):
        self._row = SimpleNamespace(
            active_provider="openai_api",
            model_mappings_json=model_mappings,
            openai_config_meta_json={},
            validation_status_json={},
            version=1,
            updated_by_user_id=None,
        )
        self._models_defaults = SimpleNamespace(
            value_json={
                "chat_model_id": "gpt-4o-mini",
                "embedding_model_id": "text-embedding-3-small",
                "embedding_batch_size": 16,
            }
        )

    def get_provider_settings(self):
        return self._row

    def get_namespace(self, namespace, key):
        assert namespace == "models"
        assert key == "defaults"
        return self._models_defaults


def test_provider_model_resolution_openai_only():
    service = ProviderService.__new__(ProviderService)
    service.db = None
    service.settings = SimpleNamespace(embedding_batch_size=16, max_upload_size_mb=100)
    service.settings_service = DummySettingsService(
        {"openai_api": {"default": "gpt-4o-mini"}}
    )
    service.secrets_service = SimpleNamespace()
    assert service.resolve_model_for_category("openai_api", "low") == "gpt-4o-mini"
    assert service.resolve_model_for_category("openai_api", "high") == "gpt-4o-mini"
