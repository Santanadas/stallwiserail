import uuid


def _register(client, email, password="Passw0rd!"):
    return client.post("/api/auth/register",
                       json={"name": "A", "email": email, "password": password})


def test_register_requires_otp_before_user_exists(app_client):
    email = f"u_{uuid.uuid4().hex[:8]}@example.com"
    r = _register(app_client, email)
    assert r.status_code == 200
    body = r.json()
    assert body["pendingOtp"] is True and body["otpId"]
    # /auth/me with nothing -> not authenticated (user row not created yet)
    assert app_client.get("/api/auth/me").status_code == 401


def test_full_register_verify_login_cycle(app_client):
    email = f"u_{uuid.uuid4().hex[:8]}@example.com"
    reg = _register(app_client, email).json()
    v = app_client.post("/api/auth/verify-otp",
                        json={"otp_id": reg["otpId"], "otp": reg["devOtp"]})
    assert v.status_code == 200
    me = v.json()
    assert me["email"] == email and me["token"]
    assert me["hasStore"] is False

    # Login is also two-step.
    li = app_client.post("/api/auth/login", json={"email": email, "password": "Passw0rd!"})
    assert li.status_code == 200 and li.json()["pendingOtp"] is True
    lv = app_client.post("/api/auth/verify-otp",
                         json={"otp_id": li.json()["otpId"], "otp": li.json()["devOtp"]})
    assert lv.status_code == 200 and lv.json()["email"] == email


def test_wrong_otp_is_rejected_and_counts_attempts(app_client):
    email = f"u_{uuid.uuid4().hex[:8]}@example.com"
    reg = _register(app_client, email).json()
    r = app_client.post("/api/auth/verify-otp", json={"otp_id": reg["otpId"], "otp": "000000"})
    assert r.status_code == 400
    assert "attempts" in r.json()["detail"].lower()


def test_login_bad_password(app_client):
    email = f"u_{uuid.uuid4().hex[:8]}@example.com"
    reg = _register(app_client, email).json()
    app_client.post("/api/auth/verify-otp", json={"otp_id": reg["otpId"], "otp": reg["devOtp"]})
    r = app_client.post("/api/auth/login", json={"email": email, "password": "wrong"})
    assert r.status_code == 401


def test_duplicate_registration_blocked_after_verify(app_client):
    email = f"u_{uuid.uuid4().hex[:8]}@example.com"
    reg = _register(app_client, email).json()
    app_client.post("/api/auth/verify-otp", json={"otp_id": reg["otpId"], "otp": reg["devOtp"]})
    r = _register(app_client, email)
    assert r.status_code == 400 and "already registered" in r.json()["detail"].lower()


def test_forgot_password_is_generic(app_client):
    r = app_client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})
    assert r.status_code == 200
    assert "if that email exists" in r.json()["message"].lower()


def test_me_and_refresh_with_bearer_token(make_seller):
    s = make_seller()
    assert s.get("/api/auth/me").json()["email"] == s.email
    r = s.post("/api/auth/refresh")
    assert r.status_code == 200 and r.json()["token"]


def test_password_min_length_enforced(app_client):
    r = _register(app_client, f"x_{uuid.uuid4().hex[:6]}@example.com", password="short")
    assert r.status_code == 422
