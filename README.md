# Private Knowledge Worker

A read-only retrieval-augmented search system for a user's Google Docs.

## Supported runtimes

- Python 3.12 or newer
- Node.js 20.19 or newer
- `uv`
- npm

## Common commands

Run `make help` to list the root commands.

```bash
make install
make dev-backend
make dev-frontend
make lint
make format-check
make test
make build
```

The backend API is served at <http://127.0.0.1:8000>, with its API information
endpoint at <http://127.0.0.1:8000/api/v1/>. The frontend development server
uses Vite's default port.

Docker Compose and database migrations are reserved for the F-003 and F-004
implementation stages. Their root commands are present so the command surface
does not change as those stages are added.
