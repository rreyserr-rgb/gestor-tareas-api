# Tests de integración para los endpoints de tareas

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from aplicacion.base_de_datos import Base, get_db
from aplicacion.principal import app

# Motor SQLite en memoria con StaticPool para aislamiento entre tests
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

# Fixture de cliente reutilizable para todos los tests
client = TestClient(app)


def setup_function():
    """Recrea las tablas antes de cada test para garantizar aislamiento."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


# ---------- Tests para update_task ----------


def test_update_pending_task_succeeds():
    """Actualizar una tarea con estado 'pending' debe funcionar correctamente."""
    response = client.post("/tasks/", json={"title": "Tarea pendiente"})
    assert response.status_code == 201
    task_id = response.json()["id"]

    response = client.patch(
        f"/tasks/{task_id}", json={"title": "Título actualizado"}
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Título actualizado"


def test_update_in_progress_task_succeeds():
    """Actualizar una tarea con estado 'in_progress' debe funcionar."""
    response = client.post(
        "/tasks/", json={"title": "Tarea en progreso", "status": "in_progress"}
    )
    assert response.status_code == 201
    task_id = response.json()["id"]

    response = client.patch(
        f"/tasks/{task_id}", json={"description": "Descripción nueva"}
    )
    assert response.status_code == 200
    assert response.json()["description"] == "Descripción nueva"


def test_update_done_task_returns_400():
    """Intentar actualizar una tarea con estado 'done' debe devolver 400."""
    response = client.post(
        "/tasks/", json={"title": "Tarea completa", "status": "done"}
    )
    assert response.status_code == 201
    task_id = response.json()["id"]

    response = client.patch(
        f"/tasks/{task_id}", json={"title": "Nuevo título"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Cannot update a completed task"


def test_update_task_to_done_then_reject_further_updates():
    """
    Mover una tarea a 'done' y luego intentar modificarla debe fallar
    con 400.
    """
    response = client.post("/tasks/", json={"title": "Tarea nueva"})
    assert response.status_code == 201
    task_id = response.json()["id"]

    response = client.patch(
        f"/tasks/{task_id}", json={"status": "done"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "done"

    response = client.patch(
        f"/tasks/{task_id}", json={"title": "Intento de cambio"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Cannot update a completed task"
