from fastapi.testclient import TestClient

def test_login_nonexistent_user(client):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "nonexistent@example.com", "password": "password123"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"

def test_register_and_login(client):
    user_data = {
        "name": "Test User",
        "email": "test@example.com",
        "password": "password123",
        "preferences": {
            "email": True,
            "push": True
        }
    }
    
    register_response = client.post("/api/v1/users/", json=user_data)
    assert register_response.status_code == 201
    assert register_response.json()["success"] is True
    
    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": "test@example.com", "password": "password123"}
    )
    assert login_response.status_code == 200
    assert "access_token" in login_response.json()["data"]
    assert "refresh_token" in login_response.json()["data"]

def test_refresh_token(client):
    user_data = {
        "name": "Test User",
        "email": "refresh@example.com",
        "password": "password123",
        "preferences": {"email": True, "push": True}
    }
    
    client.post("/api/v1/users/", json=user_data)
    
    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": "refresh@example.com", "password": "password123"}
    )
    
    refresh_token = login_response.json()["data"]["refresh_token"]
    
    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    
    assert refresh_response.status_code == 200
    assert "access_token" in refresh_response.json()["data"]

def test_invalid_refresh_token(client):
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid_token"}
    )
    
    assert response.status_code == 401