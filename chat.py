'''
1)websocket - дозволяє отримувати інфу і відправляти без перезавантаження сторінки
фастАпі - це фреймворк, що приймає запит, а мої функції будуть йому вказувати що з ними робити - мій власний API
реквест - це об'єкт з інфою про запит: звідки прийшли і що треба

2)Браузер шле "Запит" (Request)
Твій FastAPI (двигун) отримує це і готує "Відповідь" (Response).

3) async - Каже Пайтону: "Ця функція буде робити щось, що може зайняти час 
(наприклад, відправляти дані по мережі). Не чекай на неї, не блокуй всю програму.
Поки вона працює, займайся іншими справами". Це робить твій чат швидким.

4) # async працює код коли доходить до await і зразу переключається на інший код щоб його виконати але той код де await почне виконуватись коли прийде попередження що блок коду де await виконався

5) uvicorn - це сервер, що запускає сайт. 
chat:app - це вказівка запустити об'єкт app з файлу chat. 
--reload - це команда для автоматичного перезапуску сервера при змінах у коді.


'''


from fastapi import FastAPI, WebSocket, Request, Query, Body, HTTPException, status
# модуль з різними видами відповідей(текст, json, html) витягуємо лише HTML
from fastapi.responses import HTMLResponse
# помагає з шаблонами(html) він вставляє інфу з пайтона в html i відправляє користувачу дані
from fastapi.templating import Jinja2Templates

# ---- Нові імпорти для верифікації ----
import jwt
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
from typing import List

app = FastAPI()  # прийматиме інструкції для запитів
# дивиться всі html шаблони щоб зібрати
templates = Jinja2Templates(directory="templ")

# ---- Нові налаштування безпеки ----
SECRET_KEY = "my-super-secret-key-for-lab-6"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Наша "база даних" користувачів, поки що в пам'яті
fake_users_db = {}


class User(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str

# ---- Нові функції-хелпери для паролів і токенів ----


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except InvalidTokenError:
        return None

# ---- Кінець нових функцій ----


# це список в який складатиму всіх, хто зараз підключений до чату для вебсокета
active_connections: List[WebSocket] = []


# асинхронна функція що дає змогу не переривати інший код
# якщо функція працює довго(типу вона виконується і інший код виконується паралельно
# щоб не мішати один одному і не чикати один одного)
# функція бере одне повідомлення і відправляє його всім, хто зараз підключений до чату
async def broadcast(message: str):
    # перебираємо все з списку
    for connection in active_connections:
        # async працює код коли доходить до await і зразу переключається на інший код щоб його виконати але той код де await почне виконуватись коли прийде попередження що блок коду де await виконався
        await connection.send_text(message)
        # бере message і відправляє його по одному конкретному connection (кожному)


@app.get("/", response_class=HTMLResponse)
async def get_chat_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ---- Нові ендпоінти для логіну/реєстрації ----

@app.get("/login", response_class=HTMLResponse)
async def get_login_page(request: Request):
    # Цьому знадобиться новий файл templ/login.html
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/register")
async def register_user(user: User = Body(...)):
    if user.username in fake_users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Цей username вже зайнятий"
        )
    hashed_password = get_password_hash(user.password)
    fake_users_db[user.username] = hashed_password
    return {"message": f"Користувач {user.username} зареєстрований!"}


@app.post("/login", response_model=Token)
async def login_for_access_token(user: User = Body(...)):
    db_user_hash = fake_users_db.get(user.username)
    if not db_user_hash or not verify_password(user.password, db_user_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неправильний username або пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# ---- Кінець нових ендпоінтів ----


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    # Тепер ми вимагаємо 'token' при підключенні
    username = decode_token(token)

    if username is None or username not in fake_users_db:
        # Якщо "квиток" (токен) поганий, або юзера нема в нашій базі - відхиляємо
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Якщо все добре, пускаємо в чат
    await websocket.accept()
    active_connections.append(websocket)

    await broadcast(f"INFO: Користувач '{username}' приєднався. Всього: {len(active_connections)}")

    try:
        while True:
            data = await websocket.receive_text()
            # Додаємо ім'я користувача до кожного повідомлення
            await broadcast(f"{username}: {data}")

    except Exception:
        active_connections.remove(websocket)
        await broadcast(f"INFO: Користувач '{username}' вийшов. Залишилось: {len(active_connections)}")

# ФІКТИВНА ЗМІНА
