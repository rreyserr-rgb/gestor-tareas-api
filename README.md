# API de Gestión de Tareas

API REST para gestionar tareas construida con **FastAPI** y **SQLAlchemy**.

## Arranque rápido

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn aplicacion.principal:app --reload
```

La documentación interactiva (Swagger UI) queda disponible en `http://127.0.0.1:8000/docs`.

## Endpoints disponibles

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/tasks/` | Lista todas las tareas |
| GET | `/tasks/{id}` | Obtiene una tarea por id |
| GET | `/tasks/status/{status}` | Filtra tareas por estado |
| POST | `/tasks/` | Crea una nueva tarea |
| PATCH | `/tasks/{id}` | Actualiza parcialmente una tarea |
| PATCH | `/tasks/{id}/complete` | Marca una tarea como completada (`done`) |
| DELETE | `/tasks/{id}` | Elimina una tarea |

## Tests

```bash
pytest tests/ -v
```
