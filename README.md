# Secure Chat App

Quick start:

1) Install dependencies

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

2) Run API server

```bash
uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
```

3) Open frontend

Open `frontend/index.html` in a static server or your browser. The page expects the API on port 8000.

Features:
- Register and login
- JWT-based auth
- Send/receive messages
- Chat history
- WebSocket presence + live delivery