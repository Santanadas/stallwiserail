import os, pytest, requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL") or open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split("\n")[0].strip()

@pytest.fixture(scope="session")
def base_url():
    return BASE_URL.rstrip("/")

@pytest.fixture
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s

@pytest.fixture
def owner_session(api, base_url):
    r = api.post(f"{base_url}/api/auth/login", json={"email": "bongsharnipan123@gmail.com", "password": "Marketo@Admin2026"})
    assert r.status_code == 200, f"owner login failed: {r.status_code} {r.text}"
    return api
