# ADR-001: Elección de SQLite como base de datos

## Estado

**Aceptado**

## Contexto

La API de Gestión de Tareas necesita una base de datos relacional para persistir tareas con sus atributos (título, descripción, estado y fecha de creación). El proyecto es una API REST construida con FastAPI y SQLAlchemy que se ejecuta como un único proceso con Uvicorn.

Requisitos clave que condicionan la elección:

- **Simplicidad de despliegue**: la API debe poder arrancar sin depender de servicios externos.
- **Bajo coste operativo**: no se dispone de infraestructura dedicada para administrar un servidor de base de datos.
- **Volumen de datos reducido**: el modelo de dominio es sencillo (una tabla `tasks`) y no se prevé un volumen elevado de escrituras concurrentes.
- **Entorno de desarrollo ágil**: los desarrolladores deben poder clonar el repositorio y ejecutar la API sin instalar ni configurar software adicional.
- **Tests aislados**: la suite de pruebas necesita bases de datos efímeras y rápidas.

## Decisión

Se adopta **SQLite** como motor de base de datos, almacenando los datos en el archivo local `tareas.db`. SQLAlchemy actúa como capa de abstracción ORM, lo que facilita una posible migración futura a otro motor.

### Razones principales

1. **Cero configuración**: SQLite viene integrado en la biblioteca estándar de Python (`sqlite3`). No requiere instalar ni administrar un servidor de base de datos independiente.
2. **Portabilidad**: la base de datos es un único archivo que se puede copiar, respaldar o trasladar sin herramientas especiales.
3. **Rendimiento excelente para cargas de lectura**: en escenarios con predominio de lecturas y escrituras poco frecuentes, SQLite ofrece tiempos de respuesta muy bajos al no necesitar comunicación por red.
4. **Ideal para desarrollo y pruebas**: los tests usan SQLite en memoria con `StaticPool`, lo que garantiza aislamiento total y velocidad sin necesidad de levantar contenedores ni servicios auxiliares.
5. **Compatibilidad con SQLAlchemy**: `check_same_thread=False` resuelve la limitación de uso multi-hilo con FastAPI, y el ORM abstrae las particularidades del dialecto.

## Alternativas consideradas

### PostgreSQL

| Aspecto | Valoración |
|---|---|
| **Ventajas** | Soporte completo de transacciones ACID con concurrencia real (MVCC). Tipos de datos avanzados (JSONB, arrays, rangos). Escalabilidad horizontal con réplicas de lectura. Ecosistema maduro de herramientas de monitorización, respaldo y alta disponibilidad. Amplia adopción en producción empresarial. |
| **Inconvenientes** | Requiere instalar y administrar un servidor independiente (o contratar un servicio gestionado). Añade complejidad al entorno de desarrollo: cada desarrollador necesita una instancia local o un contenedor Docker. Mayor consumo de recursos (memoria y CPU) incluso para cargas ligeras. Curva de configuración inicial más alta (autenticación, `pg_hba.conf`, esquemas). |

### MySQL

| Aspecto | Valoración |
|---|---|
| **Ventajas** | Motor muy extendido con amplia comunidad y documentación. Buen rendimiento en lecturas intensivas gracias a su caché de consultas. Herramientas de administración maduras (MySQL Workbench, phpMyAdmin). Compatible con la mayoría de proveedores de hosting y servicios gestionados. |
| **Inconvenientes** | Al igual que PostgreSQL, necesita un proceso servidor independiente. Manejo de transacciones y concurrencia menos robusto que PostgreSQL (depende del motor de almacenamiento). Algunas limitaciones en tipos de datos y en cumplimiento estricto del estándar SQL. Introduce una dependencia externa que complica el despliegue para un proyecto de este tamaño. |

## Consecuencias

### Positivas

- **Despliegue inmediato**: la API arranca con `uvicorn aplicacion.principal:app --reload` sin pasos previos de infraestructura.
- **Onboarding rápido**: un nuevo desarrollador solo necesita `pip install -r requirements.txt` para tener un entorno funcional completo.
- **Tests rápidos y deterministas**: SQLite en memoria elimina efectos colaterales entre tests y reduce el tiempo de ejecución de la suite.
- **Migración viable**: al usar SQLAlchemy como ORM, cambiar a PostgreSQL o MySQL en el futuro solo requiere modificar `SQLALCHEMY_DATABASE_URL` y el driver correspondiente (e.g., `psycopg2`, `pymysql`).

### Riesgos y limitaciones a largo plazo

- **Concurrencia de escritura limitada**: SQLite utiliza un bloqueo a nivel de archivo para las escrituras. Si la API escala a múltiples procesos (workers) con escrituras frecuentes, podrían producirse errores de tipo `database is locked`.
- **Sin acceso remoto nativo**: la base de datos reside en el sistema de archivos local, lo que impide que varios servicios o réplicas accedan a los mismos datos sin mecanismos externos.
- **Subconjunto de SQL**: SQLite no soporta ciertas operaciones (`ALTER TABLE` completo, `RIGHT JOIN`, tipos estrictos), lo que podría limitar esquemas más complejos en el futuro.
- **No apto para alta disponibilidad**: no existen mecanismos nativos de replicación ni failover automático.
- **Plan de mitigación**: si el proyecto crece más allá de un único proceso o requiere acceso concurrente elevado, se deberá migrar a PostgreSQL. La abstracción proporcionada por SQLAlchemy minimiza el esfuerzo de esa transición.
