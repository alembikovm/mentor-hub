import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="mentor-hub-test-")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp}/test.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
