"""Never run the test suite against real event data or configured cloud secrets."""
import os
import tempfile

os.environ["CLOUD_CHAOS_DATABASE_URL"] = ""
os.environ["CLOUD_CHAOS_DATA_DIR"] = tempfile.mkdtemp(prefix="cloud-chaos-pytest-")
