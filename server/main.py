from datetime import datetime
from typing import Dict, List

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .auth import authenticate_user, create_access_token, get_current_user, get_password_hash
from .database import Base, engine, get_db
from .models import Message, User
from .schemas import ChatHistory, MessageCreate, MessageOut, Token, UserCreate, UserOut
from .routes import router as public_router


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Secure Chat App")

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

app.include_router(public_router)


@app.post("/auth/register", response_model=UserOut)
def register_user(payload: UserCreate, db: Session = Depends(get_db)):
	existing = db.query(User).filter(User.username == payload.username).first()
	if existing:
		raise HTTPException(status_code=400, detail="Username already taken")
	user = User(
		username=payload.username,
		password_hash=get_password_hash(payload.password),
	)
	db.add(user)
	db.commit()
	db.refresh(user)
	return user


@app.post("/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
	user = authenticate_user(db, form_data.username, form_data.password)
	if not user:
		raise HTTPException(status_code=400, detail="Incorrect username or password")
	access_token = create_access_token({"sub": str(user.id), "username": user.username})
	return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
	current_user.last_seen = datetime.utcnow()
	db.add(current_user)
	db.commit()
	db.refresh(current_user)
	return current_user


@app.post("/messages", response_model=MessageOut)
async def send_message(
	payload: MessageCreate,
	current_user: User = Depends(get_current_user),
	db: Session = Depends(get_db),
):
	recipient = db.query(User).filter(User.id == payload.recipient_id).first()
	if not recipient:
		raise HTTPException(status_code=404, detail="Recipient not found")
	message = Message(
		sender_id=current_user.id,
		recipient_id=payload.recipient_id,
		content=payload.content,
	)
	db.add(message)
	db.commit()
	db.refresh(message)

	# Push to WebSocket if recipient connected
	await manager.send_personal_message(recipient_id=payload.recipient_id, message=MessageOut.model_validate(message))
	return message


@app.get("/messages/{with_user_id}", response_model=ChatHistory)
def get_chat_history(with_user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
	messages: List[Message] = (
		db.query(Message)
		.filter(
			((Message.sender_id == current_user.id) & (Message.recipient_id == with_user_id))
			|
			((Message.sender_id == with_user_id) & (Message.recipient_id == current_user.id))
		)
		.order_by(Message.created_at.asc())
		.all()
	)
	return ChatHistory(with_user_id=with_user_id, messages=[MessageOut.model_validate(m) for m in messages])


class ConnectionManager:
	def __init__(self) -> None:
		self.user_id_to_connections: Dict[int, List[WebSocket]] = {}

	async def connect(self, user_id: int, websocket: WebSocket) -> None:
		await websocket.accept()
		self.user_id_to_connections.setdefault(user_id, []).append(websocket)

	def disconnect(self, user_id: int, websocket: WebSocket) -> None:
		connections = self.user_id_to_connections.get(user_id, [])
		if websocket in connections:
			connections.remove(websocket)
			if not connections:
				self.user_id_to_connections.pop(user_id, None)

	async def send_personal_message(self, recipient_id: int, message: MessageOut) -> None:
		for ws in list(self.user_id_to_connections.get(recipient_id, [])):
			try:
				await ws.send_json({"type": "message", "payload": message.model_dump()})
			except Exception:
				# Ignore send errors; client may have disconnected
				continue

	async def broadcast_presence(self, user_id: int, online: bool) -> None:
		payload = {"type": "presence", "payload": {"user_id": user_id, "online": online}}
		for uid, sockets in self.user_id_to_connections.items():
			for ws in sockets:
				await ws.send_json(payload)


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
	# Expect token query param for simplicity: /ws?token=...
	token = websocket.query_params.get("token")
	if not token:
		await websocket.close(code=4401)
		return

	# Lightweight token decode to attach user_id
	from jose import jwt
	from .auth import SECRET_KEY, ALGORITHM

	try:
		payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
		user_id = int(payload.get("sub"))
		if not user_id:
			raise ValueError
	except Exception:
		await websocket.close(code=4401)
		return

	await manager.connect(user_id=user_id, websocket=websocket)
	try:
		await manager.broadcast_presence(user_id=user_id, online=True)
		while True:
			data = await websocket.receive_json()
			# Echo or handle ping/pong
			if data.get("type") == "ping":
				await websocket.send_json({"type": "pong"})
	except WebSocketDisconnect:
		manager.disconnect(user_id=user_id, websocket=websocket)
		await manager.broadcast_presence(user_id=user_id, online=False)

