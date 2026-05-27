# API de Gestión de Tareas

API REST para la gestión del ciclo de vida de tareas, construida con **FastAPI** y **SQLAlchemy**. Permite crear, consultar, actualizar y eliminar tareas a través de una interfaz HTTP estandarizada. Cada tarea dispone de un identificador único, título, descripción opcional, estado (`pending`, `in_progress`, `done`) y fecha de creación asignada automáticamente.

## Requisitos previos

| Requisito | Versión mínima |
|---|---|
| Python | 3.12+ |
| pip | incluido con Python |

### Dependencias del proyecto

| Paquete | Versión | Uso |
|---|---|---|
| FastAPI | 0.136.1 | Framework web |
| SQLAlchemy | 2.0.49 | ORM y acceso a base de datos |
| Pydantic | 2.13.4 | Validación de datos |
| Uvicorn | 0.46.0 | Servidor ASGI |
| pytest | 9.0.3 | Framework de tests |
| httpx | 0.28.1 | Cliente HTTP para tests |
| anyio | 4.13.0 | Compatibilidad asíncrona para tests |

## Instalación

1. **Clonar el repositorio:**

   ```bash
   git clone https://github.com/rreyserr-rgb/gestor-tareas-api.git
   cd gestor-tareas-api
   ```

2. **Crear y activar un entorno virtual:**

   ```bash
   python -m venv venv
   # macOS / Linux
   source venv/bin/activate
   # Windows
   venv\Scripts\activate
   ```

3. **Instalar las dependencias:**

   ```bash
   pip install -r requirements.txt
   ```

## Arrancar la aplicación

```bash
uvicorn aplicacion.principal:app --reload
```

La API quedará disponible en `http://127.0.0.1:8000`.

La documentación interactiva (Swagger UI) se genera automáticamente en `http://127.0.0.1:8000/docs`.

## Endpoints

La API expone los siguientes endpoints bajo el prefijo `/tasks`:

### Listar todas las tareas

| | |
|---|---|
| **Método** | `GET` |
| **Ruta** | `/tasks/` |
| **Parámetros** | Ninguno |

**Ejemplo curl:**

```bash
curl http://127.0.0.1:8000/tasks/
```

**Ejemplo de respuesta** (`200 OK`):

```json
[
  {
    "id": 1,
    "title": "Revisar documentación",
    "description": "Revisar la documentación del sprint actual",
    "status": "pending",
    "created_at": "2025-05-27T10:30:00"
  },
  {
    "id": 2,
    "title": "Corregir bug de login",
    "description": null,
    "status": "in_progress",
    "created_at": "2025-05-27T11:00:00"
  }
]
```

---

### Obtener una tarea por id

| | |
|---|---|
| **Método** | `GET` |
| **Ruta** | `/tasks/{task_id}` |
| **Parámetros de ruta** | `task_id` (entero) — Identificador de la tarea |

**Ejemplo curl:**

```bash
curl http://127.0.0.1:8000/tasks/1
```

**Ejemplo de respuesta** (`200 OK`):

```json
{
  "id": 1,
  "title": "Revisar documentación",
  "description": "Revisar la documentación del sprint actual",
  "status": "pending",
  "created_at": "2025-05-27T10:30:00"
}
```

**Respuesta de error** (`404 Not Found`):

```json
{
  "detail": "Task not found"
}
```

---

### Filtrar tareas por estado

| | |
|---|---|
| **Método** | `GET` |
| **Ruta** | `/tasks/status/{status}` |
| **Parámetros de ruta** | `status` — Estado de la tarea. Valores válidos: `pending`, `in_progress`, `done` |

**Ejemplo curl:**

```bash
curl http://127.0.0.1:8000/tasks/status/pending
```

**Ejemplo de respuesta** (`200 OK`):

```json
[
  {
    "id": 1,
    "title": "Revisar documentación",
    "description": "Revisar la documentación del sprint actual",
    "status": "pending",
    "created_at": "2025-05-27T10:30:00"
  }
]
```

**Respuesta de error** (`422 Unprocessable Entity`):

```json
{
  "detail": [
    {
      "type": "enum",
      "loc": ["path", "status"],
      "msg": "Input should be 'pending', 'in_progress' or 'done'"
    }
  ]
}
```

---

### Crear una nueva tarea

| | |
|---|---|
| **Método** | `POST` |
| **Ruta** | `/tasks/` |
| **Cuerpo (JSON)** | `title` (string, obligatorio, 3-255 caracteres), `description` (string, opcional), `status` (string, opcional, por defecto `"pending"`) |

**Ejemplo curl:**

```bash
curl -X POST http://127.0.0.1:8000/tasks/ \
  -H "Content-Type: application/json" \
  -d '{"title": "Escribir tests unitarios", "description": "Cubrir los casos de error"}'
```

**Ejemplo de respuesta** (`201 Created`):

```json
{
  "id": 3,
  "title": "Escribir tests unitarios",
  "description": "Cubrir los casos de error",
  "status": "pending",
  "created_at": "2025-05-27T12:00:00"
}
```

**Respuesta de error** (`422 Unprocessable Entity`):

```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "title"],
      "msg": "String should have at least 3 characters"
    }
  ]
}
```

---

### Actualizar parcialmente una tarea

| | |
|---|---|
| **Método** | `PATCH` |
| **Ruta** | `/tasks/{task_id}` |
| **Parámetros de ruta** | `task_id` (entero) — Identificador de la tarea |
| **Cuerpo (JSON)** | `title` (string, opcional, 3-255 caracteres), `description` (string, opcional), `status` (string, opcional) |

Solo se actualizan los campos enviados en el cuerpo de la petición. Las tareas en estado `done` no pueden modificarse.

**Ejemplo curl:**

```bash
curl -X PATCH http://127.0.0.1:8000/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'
```

**Ejemplo de respuesta** (`200 OK`):

```json
{
  "id": 1,
  "title": "Revisar documentación",
  "description": "Revisar la documentación del sprint actual",
  "status": "in_progress",
  "created_at": "2025-05-27T10:30:00"
}
```

**Respuesta de error** (`404 Not Found`):

```json
{
  "detail": "Task not found"
}
```

**Respuesta de error** (`400 Bad Request`) — tarea ya completada:

```json
{
  "detail": "Cannot modify a completed task"
}
```

---

### Eliminar una tarea

| | |
|---|---|
| **Método** | `DELETE` |
| **Ruta** | `/tasks/{task_id}` |
| **Parámetros de ruta** | `task_id` (entero) — Identificador de la tarea |

**Ejemplo curl:**

```bash
curl -X DELETE http://127.0.0.1:8000/tasks/1
```

**Respuesta exitosa:** `204 No Content` (sin cuerpo).

**Respuesta de error** (`404 Not Found`):

```json
{
  "detail": "Task not found"
}
```

## Ejecutar los tests

```bash
pytest tests/ -v
```

Los tests utilizan una base de datos SQLite en memoria con `StaticPool` para garantizar el aislamiento entre casos de prueba. No afectan al archivo `tareas.db` de producción.

## Estructura del proyecto

```
gestor-tareas-api/
├── aplicacion/                  # Paquete principal de la aplicación
│   ├── __init__.py
│   ├── principal.py             # Punto de entrada: instancia de FastAPI y registro de routers
│   ├── base_de_datos.py         # Configuración del engine, sesión de SQLAlchemy y dependencia get_db
│   ├── modelos.py               # Modelos ORM (tabla tasks, enum TaskStatus)
│   ├── esquemas.py              # Esquemas Pydantic de entrada (TaskCreate, TaskUpdate) y respuesta (TaskResponse)
│   └── rutas/                   # Definición de endpoints REST agrupados por recurso
│       ├── __init__.py
│       └── tareas.py            # Endpoints CRUD de tareas (/tasks)
├── tests/                       # Suite de tests automatizados
│   ├── __init__.py
│   └── test_tasks.py            # Tests con pytest, TestClient de FastAPI y SQLite en memoria
├── requirements.txt             # Dependencias de producción y desarrollo
├── AGENTS.md                    # Convenciones del proyecto y guía para contribuidores
├── .gitignore                   # Archivos excluidos del control de versiones
└── README.md                    # Documentación del proyecto
```
