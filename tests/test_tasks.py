# Tests de la API de gestión de tareas con pytest y FastAPI TestClient
#
# COBERTURA:
#   - POST  /tasks       → crear tarea correctamente (201)
#   - POST  /tasks       → título vacío o <3 caracteres (422)
#   - GET   /tasks       → listar tareas (vacío y con datos)
#   - GET   /tasks/{id}  → id inexistente (404)
#   - PATCH /tasks/{id}  → tarea en estado "done" (400)
#   - PATCH /tasks/{id}  → id inexistente (404)
#   - DELETE /tasks/{id} → id inexistente (404)
#   - DELETE /tasks/     → eliminar todas las tareas (204) y verificar lista vacía
#   - DELETE /tasks/     → sin tareas existentes (404)

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
    # Sustituye la dependencia de BD real por la sesión de test
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    # 1. Crear tablas en el engine de test antes de instanciar el TestClient;
    #    principal.py ya no llama create_all al importarse (usa lifespan),
    #    así que aquí tenemos control total sobre qué engine se usa
    Base.metadata.create_all(bind=engine_test)

    # 2. Sobreescribir la dependencia de BD para que todas las peticiones usen engine_test
    app.dependency_overrides[get_db] = override_get_db

    # 3. TestClient sin context manager: no dispara el lifespan de la app,
    #    evitando que el create_all de producción interfiera con engine_test
    yield TestClient(app)

    # 4. Limpieza al terminar cada test
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine_test)


# ---------------------------------------------------------------------------
# Happy path: crear tarea
# ---------------------------------------------------------------------------

def test_crear_tarea_correctamente(client):
    # Verifica que una tarea válida se crea y devuelve los campos esperados
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
    # Sin tareas creadas la respuesta debe ser una lista vacía
    response = client.get("/tasks/")

    assert response.status_code == 200
    assert response.json() == []


def test_listar_tareas_con_datos(client):
    # Crea dos tareas y comprueba que ambas aparecen en el listado
    client.post("/tasks/", json={"title": "Primera tarea"})
    client.post("/tasks/", json={"title": "Segunda tarea"})

    response = client.get("/tasks/")

    assert response.status_code == 200
    assert len(response.json()) == 2


# ---------------------------------------------------------------------------
# Casos de error
# ---------------------------------------------------------------------------

def test_crear_tarea_titulo_vacio(client):
    # Título vacío: violación de min_length=3 → 422
    response = client.post("/tasks/", json={"title": ""})
    assert response.status_code == 422


def test_crear_tarea_titulo_demasiado_corto(client):
    # Título de 2 caracteres: violación de min_length=3 → 422
    response = client.post("/tasks/", json={"title": "ab"})
    assert response.status_code == 422


def test_obtener_tarea_no_encontrada(client):
    # GET con id inexistente → 404
    response = client.get("/tasks/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


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


def test_actualizar_tarea_no_encontrada(client):
    # PATCH con id inexistente → 404
    response = client.patch("/tasks/9999", json={"title": "Nuevo titulo"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_eliminar_tarea_no_encontrada(client):
    # DELETE con id inexistente → 404
    response = client.delete("/tasks/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


# ---------------------------------------------------------------------------
# Happy path: eliminar todas las tareas
# ---------------------------------------------------------------------------

def test_eliminar_todas_las_tareas(client):
    # Crea varias tareas, las elimina de golpe y verifica que la lista quede vacía
    client.post("/tasks/", json={"title": "Tarea uno"})
    client.post("/tasks/", json={"title": "Tarea dos"})
    client.post("/tasks/", json={"title": "Tarea tres"})

    response = client.delete("/tasks/")
    assert response.status_code == 204

    # Tras el borrado masivo la lista debe estar vacía
    lista = client.get("/tasks/")
    assert lista.status_code == 200
    assert lista.json() == []


# ---------------------------------------------------------------------------
# Caso de error: eliminar todas sin tareas existentes
# ---------------------------------------------------------------------------

def test_eliminar_todas_sin_tareas(client):
    # DELETE /tasks/ sin tareas previas → 404
    response = client.delete("/tasks/")
    assert response.status_code == 404
    assert response.json()["detail"] == "No tasks to delete"
