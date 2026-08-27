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

## Google Cloud setup

In [Google Cloud Console](https://console.cloud.google.com/):

1. Create or select a project.
2. Enable the Google Drive API and Google Docs API.
3. Configure the OAuth consent screen as an External app during development.
4. Add these scopes:
   - `openid`
   - `email`
   - `profile`
   - `https://www.googleapis.com/auth/drive.readonly`
   - `https://www.googleapis.com/auth/documents.readonly`
5. Add development accounts under Test users.
6. Create an OAuth client ID for a Web application.
7. Add these local JavaScript origins:
   - `http://127.0.0.1:5173`
   - `http://localhost:5173`
8. Add these local redirect URIs:
   - `http://127.0.0.1:8000/api/v1/auth/google/callback`
   - `http://localhost:8000/api/v1/auth/google/callback`

For a deployed instance, add its frontend origin and backend callback URI to
the same OAuth client. Copy the client ID and secret into the local `.env`
file; do not commit them.

The backend API is served at <http://127.0.0.1:8000>, with its API information
endpoint at <http://127.0.0.1:8000/api/v1/>. The frontend development server
uses Vite's default port.

Docker Compose and database migrations are reserved for the F-003 and F-004
implementation stages. Their root commands are present so the command surface
does not change as those stages are added.
