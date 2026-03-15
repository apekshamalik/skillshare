import pytest
from httpx import AsyncClient


class TestUserRegistration:
    """Test user registration workflows"""
    
    @pytest.mark.asyncio
    async def test_register_user_success(self, test_client: AsyncClient):
        """Test successful user registration"""
        user_data = {
            "first_name": "John",
            "last_name": "Doe",
            "username": "johndoe",
            "email": "john@example.com",
            "password": "securepassword",
            "bio": "Test bio"
        }
        
        response = await test_client.post("/users/register", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "johndoe"
        assert data["email"] == "john@example.com"
        assert "password" not in data  # Password should not be in response
        assert "password_hash" not in data
        assert "id" in data
    
    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, test_client: AsyncClient, test_user):
        """Test that duplicate usernames are rejected"""
        user_data = {
            "first_name": "Jane",
            "last_name": "Doe",
            "username": "testuser",  # Same as test_user
            "email": "different@example.com",
            "password": "password123",
            "bio": ""
        }
        
        response = await test_client.post("/users/register", json=user_data)
        
        assert response.status_code == 400
        assert "Username already taken" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, test_client: AsyncClient, test_user):
        """Test that duplicate emails are rejected"""
        user_data = {
            "first_name": "Jane",
            "last_name": "Doe",
            "username": "janedoe",
            "email": "test@example.com",  # Same as test_user
            "password": "password123",
            "bio": ""
        }
        
        response = await test_client.post("/users/register", json=user_data)
        
        assert response.status_code == 400
        assert "Email already in use" in response.json()["detail"]


class TestUserLogin:
    """Test user login workflows"""
    
    @pytest.mark.asyncio
    async def test_login_success(self, test_client: AsyncClient, test_user):
        """Test successful login with username"""
        response = await test_client.post("/users/login", json={
            "username_or_email": "testuser",
            "password": "password123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    async def test_login_with_email(self, test_client: AsyncClient, test_user):
        """Test successful login with email"""
        response = await test_client.post("/users/login", json={
            "username_or_email": "test@example.com",
            "password": "password123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
    
    @pytest.mark.asyncio
    async def test_login_wrong_password(self, test_client: AsyncClient, test_user):
        """Test login with wrong password"""
        response = await test_client.post("/users/login", json={
            "username_or_email": "testuser",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, test_client: AsyncClient):
        """Test login with non-existent user"""
        response = await test_client.post("/users/login", json={
            "username_or_email": "nonexistent",
            "password": "password123"
        })
        
        assert response.status_code == 401


class TestUserProfile:
    """Test user profile operations"""
    
    @pytest.mark.asyncio
    async def test_get_own_profile(self, test_client: AsyncClient, test_user):
        """Test getting own profile with authentication"""
        response = await test_client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_get_profile_without_auth(self, test_client: AsyncClient):
        """Test that getting own profile without auth fails"""
        response = await test_client.get("/users/me")
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_update_profile(self, test_client: AsyncClient, test_user):
        """Test updating user profile"""
        update_data = {
            "first_name": "Updated",
            "bio": "Updated bio"
        }
        
        response = await test_client.put(
            "/users/me",
            json=update_data,
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Updated"
        assert data["bio"] == "Updated bio"
        assert data["last_name"] == "User"  # Unchanged
    
    @pytest.mark.asyncio
    async def test_get_user_by_id(self, test_client: AsyncClient, test_user):
        """Test getting user profile by ID (public route)"""
        user_id = test_user["user"]["id"]
        
        response = await test_client.get(f"/users/{user_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"