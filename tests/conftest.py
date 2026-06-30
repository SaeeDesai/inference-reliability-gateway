import os
# Ensure imports that read GROQ_API_KEY don't fail in test/CI environments.
# Real backend calls are never made in tests (we use mocks/fakes).
os.environ.setdefault("GROQ_API_KEY", "test-dummy-key")
