import os
import sys
import threading

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from werkzeug.serving import make_server

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app import create_app  # noqa: E402

PORT = 5001
BASE_URL = f"http://127.0.0.1:{PORT}"


@pytest.fixture(scope="session")
def app(tmp_path_factory):
    db_file = tmp_path_factory.mktemp("db") / "test_bank.db"
    return create_app(str(db_file))


@pytest.fixture(scope="session", autouse=True)
def live_server(app):
    server = make_server("127.0.0.1", PORT, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield
    server.shutdown()


@pytest.fixture(autouse=True)
def fresh_db(app):
    """Every test starts with demo/demo123 and a $1,000.00 balance."""
    app.reset_db()


@pytest.fixture
def driver():
    opts = webdriver.ChromeOptions()
    if os.environ.get("HEADED") != "1":
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1280,900")
    drv = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
    drv.implicitly_wait(3)
    yield drv
    drv.quit()
