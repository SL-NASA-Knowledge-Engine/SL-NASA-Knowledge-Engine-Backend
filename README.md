# SL-NASA-Knowledge-Engine-Backend

Breve guía para desarrollar y ejecutar el backend localmente.

## Requisitos
- Python 3.11+ (asegúrate de usar la misma versión en el entorno)
- Git (opcional)

## Preparar un entorno virtual (Windows, PowerShell)
1. Abrir PowerShell en la carpeta del proyecto:

```powershell
Set-Location C:\Users\user\Desktop\SL-NASA-Knowledge-Engine-Backend
```

2. Crear el virtualenv y activarlo:

```powershell
python -m venv .venv
# Si PowerShell bloquea la ejecución del script, permite temporalmente la ejecución en esta sesión:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process -Force
.\.venv\Scripts\Activate.ps1
```

Cuando el entorno está activado verás el prefijo `(.venv)` en el prompt.

## Instalar dependencias
Con el venv activado ejecuta:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Configurar variables de entorno
El proyecto usa `.env` para configuración (se incluye `.env.example`). Crea tu `.env` local copiando el ejemplo y completando valores sensibles:

```powershell
Copy-Item .env.example .env
notepad .env    # o 'code .env' si usas VS Code
```

Variables importantes (ejemplo):

```
NEO4J_URI=neo4j+s://<your-host>
NEO4J_USER=<username>
NEO4J_PASSWORD=<password>
OPENAI_API_KEY=...
```

> Nota: el servicio está diseñado para que la aplicación NO arranque si no puede conectar con Neo4j (startup fallará). Asegúrate de que las variables de Neo4j son correctas antes de ejecutar.

## Ejecutar la aplicación (desarrollo)
Con el venv activado y `.env` configurado, ejecuta:

```powershell
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Abrir en el navegador: http://127.0.0.1:8000/

API docs (Swagger): http://127.0.0.1:8000/docs

## Endpoints de ejemplo
- `GET /api/v1/hello` — endpoint simple de prueba (devuelve "Hello World").
- `GET /api/v1/neo4j/nodes?limit=10` — ejemplo para ejecutar una query en Neo4j (si está implementado en router).

## Troubleshooting rápido
- Si ves `ModuleNotFoundError: No module named 'neo4j'`: instala con `python -m pip install neo4j` dentro del venv.
- Si el servidor falla en startup por errores de Neo4j: revisa `.env` y la conectividad de red al host Neo4j. Los errores de inicio se registran en la salida de Uvicorn.
- Si PowerShell bloquea la activación del venv: usa `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force` antes de activar.

## Buenas prácticas
- No subas tu `.env` al repositorio. `.gitignore` ya lo excluye.
- Congela versiones para reproducibilidad: `python -m pip freeze > requirements-locked.txt`.

Si quieres, puedo añadir ejemplos de queries y un `scripts/test_neo4j.py` que pruebe la conectividad (sin exponer credenciales). Dime si lo añado.