import uuid
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.config import settings

client = TestClient(app)

def test_admin_login_and_list_users():
    # 1. Login como admin
    login_res = client.post("/api/v1/auth/login", json={
        "username": settings.ADMIN_USER,
        "password": settings.ADMIN_PASSWORD,
        "role": "administrador"
    })
    assert login_res.status_code == 200
    assert login_res.json()["role"] == "administrador"

    # 2. Listar usuarios como admin
    list_res = client.get("/api/v1/admin/users")
    assert list_res.status_code == 200
    data = list_res.json()
    assert "users" in data
    assert data["total"] >= 1
    usernames = [u["username"] for u in data["users"]]
    assert settings.ADMIN_USER in usernames

def test_non_admin_cannot_list_users():
    # Iniciar sesión como investigador normal
    login_res = client.post("/api/v1/auth/login", json={
        "username": settings.ACCREDITED_USER,
        "password": settings.ACCREDITED_PASSWORD,
        "role": "investigador"
    })
    assert login_res.status_code == 200

    # Intentar acceder al endpoint de administración
    list_res = client.get("/api/v1/admin/users")
    assert list_res.status_code == 403

def test_create_user_and_first_login_flow():
    # 1. Admin crea usuario individual sin especificar contraseña
    admin_login = client.post("/api/v1/auth/login", json={
        "username": settings.ADMIN_USER,
        "password": settings.ADMIN_PASSWORD,
        "role": "administrador"
    })
    assert admin_login.status_code == 200

    u_tag = uuid.uuid4().hex[:6]
    test_user = f"patricio.alvarez_{u_tag}"
    create_res = client.post("/api/v1/admin/users", json={
        "username": test_user,
        "email": f"{test_user}@espoch.edu.ec",
        "full_name": "Patricio Alvarez",
        "role": "investigador"
    })
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert created_data["username"] == test_user
    assert created_data["must_change_password"] is True

    # 2. Usuario inicia sesión con su primera contraseña (nombre.apellido)
    user_login = client.post("/api/v1/auth/login", json={
        "username": test_user,
        "password": test_user,  # Por defecto nombre.apellido
        "role": "investigador"
    })
    assert user_login.status_code == 200
    user_data = user_login.json()
    assert user_data["must_change_password"] is True

    # 3. Usuario cambia su contraseña obligatoria
    new_pwd = "MiNuevaClaveSegura2026#"
    change_res = client.post("/api/v1/auth/change-password", json={
        "current_password": test_user,
        "new_password": new_pwd
    })
    assert change_res.status_code == 200
    assert change_res.json()["must_change_password"] is False

    # 4. Probar que la contraseña vieja ya no funciona
    fail_login = client.post("/api/v1/auth/login", json={
        "username": test_user,
        "password": test_user,
        "role": "investigador"
    })
    assert fail_login.status_code == 401

    # 5. Probar que la nueva contraseña funciona y ya no pide cambio
    ok_login = client.post("/api/v1/auth/login", json={
        "username": test_user,
        "password": new_pwd,
        "role": "investigador"
    })
    assert ok_login.status_code == 200
    assert ok_login.json()["must_change_password"] is False

def test_bulk_import_users():
    # Admin inicia sesión
    client.post("/api/v1/auth/login", json={
        "username": settings.ADMIN_USER,
        "password": settings.ADMIN_PASSWORD,
        "role": "administrador"
    })

    u_tag = uuid.uuid4().hex[:6]
    user1 = f"diana.morales_{u_tag}"
    user2 = f"fernando.castro_{u_tag}"

    bulk_data = {
        "users": [
            {
                "username": user1,
                "email": f"{user1}@espoch.edu.ec",
                "full_name": "Diana Morales",
                "role": "investigador"
            },
            {
                "username": user2,
                "email": f"{user2}@espoch.edu.ec",
                "full_name": "Fernando Castro",
                "role": "auditor"
            }
        ]
    }
    res = client.post("/api/v1/admin/users/bulk-import", json=bulk_data)
    assert res.status_code == 200
    data = res.json()
    assert data["imported_count"] == 2
    assert len(data["created_users"]) == 2

    # Verificar que el segundo usuario puede ingresar con su username como contraseña inicial
    u2_login = client.post("/api/v1/auth/login", json={
        "username": user2,
        "password": user2,
        "role": "auditor"
    })
    assert u2_login.status_code == 200
    assert u2_login.json()["role"] == "auditor"
    assert u2_login.json()["must_change_password"] is True

def test_admin_reset_password_and_toggle_active():
    # Admin inicia sesión
    client.post("/api/v1/auth/login", json={
        "username": settings.ADMIN_USER,
        "password": settings.ADMIN_PASSWORD,
        "role": "administrador"
    })

    # Crear usuario para test
    u_tag = uuid.uuid4().hex[:6]
    target_user = f"roberto.guaman_{u_tag}"
    create_res = client.post("/api/v1/admin/users", json={
        "username": target_user,
        "email": f"{target_user}@espoch.edu.ec",
        "full_name": "Roberto Guaman",
        "role": "investigador"
    })
    assert create_res.status_code == 201
    uid = create_res.json()["id"]

    # Desactivar usuario
    toggle_res = client.patch(f"/api/v1/admin/users/{uid}/toggle-active")
    assert toggle_res.status_code == 200
    assert toggle_res.json()["is_active"] is False

    # El usuario desactivado no puede loguearse
    blocked_login = client.post("/api/v1/auth/login", json={
        "username": target_user,
        "password": target_user,
        "role": "investigador"
    })
    assert blocked_login.status_code == 401

    # Reactivar usuario
    reactivate_res = client.patch(f"/api/v1/admin/users/{uid}/toggle-active")
    assert reactivate_res.status_code == 200
    assert reactivate_res.json()["is_active"] is True

    # Restablecer contraseña
    reset_res = client.post(f"/api/v1/admin/users/{uid}/reset-password")
    assert reset_res.status_code == 200
    assert reset_res.json()["temp_password"] == target_user

    # Loguearse con la clave restablecida
    login_ok = client.post("/api/v1/auth/login", json={
        "username": target_user,
        "password": target_user,
        "role": "investigador"
    })
    assert login_ok.status_code == 200
    assert login_ok.json()["must_change_password"] is True
