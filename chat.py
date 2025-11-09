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


from fastapi import FastAPI, WebSocket, Request
# модуль з різними видами відповідей(текст, json, html) витягуємо лише HTML
from fastapi.responses import HTMLResponse
# помагає з шаблонами(html) він вставляє інфу з пайтона в html i відправляє користувачу дані
from fastapi.templating import Jinja2Templates

app = FastAPI()  # прийматиме інструкції для запитів
# дивиться всі html шаблони щоб зібрати
templates = Jinja2Templates(directory="templ")

# це список в який складатиму всіх, хто зараз підключений до чату для вебсокета
active_connections = []


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


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)

    await broadcast(f"Приєднався новий користувач. Всього: {len(active_connections)}")

    try:
        while True:
            data = await websocket.receive_text()
            await broadcast(f"Повідомлення: {data}")

    except Exception:
        active_connections.remove(websocket)
        await broadcast(f"Користувач вийшов. Залишилось: {len(active_connections)}")
