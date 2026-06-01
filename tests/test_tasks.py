# Tests de regresión para los bugs corregidos en la capa de validación
#
# COBERTURA:
#   - POST  /tasks       → crear tarea correctamente (201)
#   - POST  /tasks       → título vacío (422)
#   - POST  /tasks       → título < 3 caracteres (422)
#   - GET   /tasks       → listar tareas (vacío y con datos)
#   - GET   /tasks/{id}  → id inexistente (404)
#   - PATCH /tasks/{id}  → tarea en estado "done" no se puede modificar (400)
#   - PATCH /tasks/{id}  → transición a "done" sí está permitida (200)
#   - PATCH /tasks/{id}  → id inexistente (404)
#   - DELETE /tasks/{id} → id inexistente (404)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from aplicacion.base_de_datos import Base, get_db
from aplicacion.principal import app

# StaticPool garantiza que todas las sesiones comparten la misma conexión en memoria;
# sin él cada sesión abriría una conexión nueva y vería una base de datos vacía distinta
engine_test = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    Base.metadata.create_all(bind=engine_test)
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine_test)


# ---------------------------------------------------------------------------
# Happy path: crear tarea
# ---------------------------------------------------------------------------

def test_crear_tarea_correctamente(client):
    payload = {"title": "Tarea de prueba", "description": "Descripción de ejemplo"}
    response = client.post("/tasks/", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Tarea de prueba"
    assert data["description"] == "Descripción de ejemplo"
    assert data["status"] == "pending"
    assert "id" in data
    assert "created_at" in data


# ---------------------------------------------------------------------------
# Happy path: listar tareas
# ---------------------------------------------------------------------------

def test_listar_tareas_vacio(client):
    response = client.get("/tasks/")

    assert response.status_code == 200
    assert response.json() == []


def test_listar_tareas_con_datos(client):
    client.post("/tasks/", json={"title": "Primera tarea"})
    client.post("/tasks/", json={"title": "Segunda tarea"})

    response = client.get("/tasks/")

    assert response.status_code == 200
    assert len(response.json()) == 2


# ---------------------------------------------------------------------------
# Regresión Bug 1: validación de longitud mínima del título
# ---------------------------------------------------------------------------

def test_crear_tarea_titulo_vacio(client):
    # Título vacío debe rechazarse con 422
    response = client.post("/tasks/", json={"title": ""})
    assert response.status_code == 422


def test_crear_tarea_titulo_demasiado_corto(client):
    # Título de 2 caracteres: violación de min_length=3 → 422
    response = client.post("/tasks/", json={"title": "ab"})
    assert response.status_code == 422


def test_crear_tarea_titulo_limite_inferior(client):
    # Título de exactamente 3 caracteres debe aceptarse
    response = client.post("/tasks/", json={"title": "abc"})
    assert response.status_code == 201
    assert response.json()["title"] == "abc"


# ---------------------------------------------------------------------------
# Regresión Bug 2: guarda en update_task comprueba estado actual de la tarea
# ---------------------------------------------------------------------------

def test_actualizar_tarea_completada(client):
    # Crear una tarea y marcarla como "done"; un PATCH posterior debe devolver 400
    created = client.post("/tasks/", json={"title": "Tarea a completar"}).json()
    task_id = created["id"]

    # La primera transición a "done" sí está permitida
    finalizar = client.patch(f"/tasks/{task_id}", json={"status": "done"})
    assert finalizar.status_code == 200
    assert finalizar.json()["status"] == "done"

    # Cualquier modificación posterior debe rechazarse con 400
    response = client.patch(f"/tasks/{task_id}", json={"title": "Nuevo titulo"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Cannot modify a completed task"


def test_actualizar_tarea_completada_cambio_estado(client):
    # Intentar cambiar el estado de una tarea "done" también debe rechazarse
    created = client.post("/tasks/", json={"title": "Tarea done"}).json()
    task_id = created["id"]

    client.patch(f"/tasks/{task_id}", json={"status": "done"})

    response = client.patch(f"/tasks/{task_id}", json={"status": "pending"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Cannot modify a completed task"


def test_transicion_a_done_permitida(client):
    # Verificar que la transición a "done" sí funciona desde otro estado
    created = client.post("/tasks/", json={"title": "Tarea pendiente"}).json()
    task_id = created["id"]

    response = client.patch(f"/tasks/{task_id}", json={"status": "done"})
    assert response.status_code == 200
    assert response.json()["status"] == "done"


# ---------------------------------------------------------------------------
# Casos de error generales
# ---------------------------------------------------------------------------

def test_obtener_tarea_no_encontrada(client):
    response = client.get("/tasks/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_actualizar_tarea_no_encontrada(client):
    response = client.patch("/tasks/9999", json={"title": "Nuevo titulo"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_eliminar_tarea_no_encontrada(client):
    response = client.delete("/tasks/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"
