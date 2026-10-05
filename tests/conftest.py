import os
import shutil
import tempfile
import pytest
from pathlib import Path

# Ensure testing uses a clean temp directory
@pytest.fixture(scope="session")
def test_temp_dir():
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)
