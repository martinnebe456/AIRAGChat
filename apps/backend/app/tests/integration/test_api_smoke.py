import os

import pytest


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS") != "1",
    reason="Set RUN_INTEGRATION_TESTS=1 and provide a live local stack to run integration tests.",
)


def test_placeholder_integration_smoke():
    # Placeholder to keep the integration test suite structure in place.
    # Real integration tests should target the Docker Compose stack and cover:
    # auth, RBAC, upload/ingestion, chat retrieval, provider switching, eval runs.
    assert True

