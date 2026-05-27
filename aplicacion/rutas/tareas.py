# Definición de los endpoints REST para la gestión de tareas

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from aplicacion.base_de_datos import get_db
from aplicacion.esquemas import TaskCreate, TaskResponse, TaskUpdate
from aplicacion.modelos import Task, TaskStatus

# Router con prefijo /tasks; agrupa todos los endpoints de tareas
router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/", response_model=List[TaskResponse])
def list_tasks(db: Session = Depends(get_db)):
    """Devuelve la lista completa de tareas almacenadas.

    Args:
        db (Session): Sesión de base de datos inyectada por
            FastAPI mediante la dependencia ``get_db``.

    Returns:
        list[Task]: Todas las tareas registradas en la base
            de datos.
    """
    return db.query(Task).all()


@router.get("/status/{status}", response_model=List[TaskResponse])
def list_tasks_by_status(status: TaskStatus, db: Session = Depends(get_db)):
    """Devuelve las tareas filtradas por el estado indicado.

    Args:
        status (TaskStatus): Estado por el que se filtran las
            tareas (``pending``, ``in_progress`` o ``done``).
        db (Session): Sesión de base de datos inyectada por
            FastAPI mediante la dependencia ``get_db``.

    Returns:
        list[Task]: Tareas cuyo estado coincide con el valor
            proporcionado.
    """
    return db.query(Task).filter(Task.status == status).all()


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    """Devuelve una tarea por su identificador.

    Args:
        task_id (int): Identificador único de la tarea.
        db (Session): Sesión de base de datos inyectada por
            FastAPI mediante la dependencia ``get_db``.

    Returns:
        Task: La tarea correspondiente al identificador
            proporcionado.

    Raises:
        HTTPException: Error 404 si no existe ninguna tarea
            con el identificador indicado.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    """Crea una nueva tarea y devuelve el recurso creado.

    Args:
        payload (TaskCreate): Datos de la tarea a crear.
            Solo el título es obligatorio; la descripción y
            el estado son opcionales.
        db (Session): Sesión de base de datos inyectada por
            FastAPI mediante la dependencia ``get_db``.

    Returns:
        Task: La tarea recién creada con todos sus campos,
            incluidos ``id`` y ``created_at`` generados por
            la base de datos.
    """
    task = Task(**payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)):
    """Actualiza parcialmente una tarea existente.

    Solo se modifican los campos incluidos en el cuerpo de la
    petición. Las tareas con estado ``done`` no pueden
    modificarse.

    Args:
        task_id (int): Identificador único de la tarea a
            actualizar.
        payload (TaskUpdate): Campos a modificar. Todos son
            opcionales (actualización parcial tipo PATCH).
        db (Session): Sesión de base de datos inyectada por
            FastAPI mediante la dependencia ``get_db``.

    Returns:
        Task: La tarea actualizada con los nuevos valores
            aplicados.

    Raises:
        HTTPException: Error 404 si no existe ninguna tarea
            con el identificador indicado.
        HTTPException: Error 400 si la tarea ya está
            completada (estado ``done``).
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    # Una tarea ya completada no puede modificarse
    if task.status == TaskStatus.done:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify a completed task",
        )
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """Elimina una tarea de la base de datos.

    Args:
        task_id (int): Identificador único de la tarea a
            eliminar.
        db (Session): Sesión de base de datos inyectada por
            FastAPI mediante la dependencia ``get_db``.

    Raises:
        HTTPException: Error 404 si no existe ninguna tarea
            con el identificador indicado.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    db.delete(task)
    db.commit()
