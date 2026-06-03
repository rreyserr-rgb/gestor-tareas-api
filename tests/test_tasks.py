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
    payload = {"title": "Tarea de prueba", "description": "Descripción de ejemplo", "categoria": "General"}
    response = client.post("/tasks/", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Tarea de prueba"
    assert data["description"] == "Descripción de ejemplo"
    assert data["status"] == "pending"
    assert data["categoria"] == "General"
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
    client.post("/tasks/", json={"title": "Primera tarea", "categoria": "Trabajo"})
    client.post("/tasks/", json={"title": "Segunda tarea", "categoria": "Trabajo"})

    response = client.get("/tasks/")

    assert response.status_code == 200
    assert len(response.json()) == 2


# ---------------------------------------------------------------------------
# Filtro por estado en list_tasks
# ---------------------------------------------------------------------------

def test_filtrar_tareas_por_status(client):
    # Crea tareas con distintos estados y filtra solo las pendientes
    t1 = client.post("/tasks/", json={"title": "Tarea pendiente"}).json()
    t2 = client.post("/tasks/", json={"title": "Tarea en progreso"}).json()
    client.patch(f"/tasks/{t2['id']}", json={"status": "in_progress"})

    response = client.get("/tasks/", params={"status": "pending"})

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == t1["id"]


def test_filtrar_tareas_por_status_sin_resultados(client):
    # Si no hay tareas con el estado indicado, devuelve lista vacía
    client.post("/tasks/", json={"title": "Tarea pendiente"})

    response = client.get("/tasks/", params={"status": "done"})

    assert response.status_code == 200
    assert response.json() == []


def test_filtrar_tareas_status_invalido(client):
    # Un estado no válido devuelve 422
    response = client.get("/tasks/", params={"status": "invalid"})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Parámetro limit en list_tasks
# ---------------------------------------------------------------------------

def test_limit_devuelve_cantidad_indicada(client):
    # Crea 3 tareas y comprueba que limit=2 devuelve solo 2
    for i in range(3):
        client.post("/tasks/", json={"title": f"Tarea {i}"})

    response = client.get("/tasks/", params={"limit": 2})

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_limit_mayor_que_total(client):
    # Si limit supera el total de tareas, devuelve todas las existentes
    client.post("/tasks/", json={"title": "Única tarea"})

    response = client.get("/tasks/", params={"limit": 100})

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_limit_cero_es_invalido(client):
    # limit=0 viola la restricción ge=1 → 422
    response = client.get("/tasks/", params={"limit": 0})
    assert response.status_code == 422


def test_limit_negativo_es_invalido(client):
    # Un valor negativo viola la restricción ge=1 → 422
    response = client.get("/tasks/", params={"limit": -1})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Combinación de status y limit
# ---------------------------------------------------------------------------

def test_filtrar_por_status_con_limit(client):
    # Crea 3 tareas pendientes y filtra con limit=2
    for i in range(3):
        client.post("/tasks/", json={"title": f"Tarea {i}"})

    response = client.get("/tasks/", params={"status": "pending", "limit": 2})

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(t["status"] == "pending" for t in data)


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
    created = client.post("/tasks/", json={"title": "Tarea a completar", "categoria": "Personal"}).json()
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
# Tests del campo categoria
# ---------------------------------------------------------------------------

def test_crear_tarea_con_categoria(client):
    payload = {"title": "Tarea con categoría", "categoria": "Trabajo"}
    response = client.post("/tasks/", json=payload)
    assert response.status_code == 201
    assert response.json()["categoria"] == "Trabajo"


def test_crear_tarea_sin_categoria(client):
    payload = {"title": "Tarea sin categoría"}
    response = client.post("/tasks/", json=payload)
    assert response.status_code == 201
    assert response.json()["categoria"] is None


def test_actualizar_categoria(client):
    created = client.post("/tasks/", json={"title": "Tarea"}).json()
    task_id = created["id"]
    response = client.patch(f"/tasks/{task_id}", json={"categoria": "Urgente"})
    assert response.status_code == 200
    assert response.json()["categoria"] == "Urgente"
