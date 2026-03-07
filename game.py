import os
import json
import sqlite3
from datetime import datetime, timedelta
from textwrap import shorten
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

DB_PATH = "game.db"
INITIAL_DATE = "2016-01-01"
DEFAULT_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEFAULT_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not API_KEY:
    raise ValueError("Не найден DEEPSEEK_API_KEY в .env")


AVAILABLE_COUNTRIES = [
    "Россия",
    "США",
    "Китай",
    "Германия",
    "Франция",
    "Великобритания",
    "Украина",
    "Япония",
    "Индия",
    "Турция",
    "Польша",
    "Бразилия",
]

WORLD_COUNTRIES = [
    "Россия",
    "США",
    "Китай",
    "Германия",
    "Франция",
    "Великобритания",
    "Украина",
    "Япония",
    "Индия",
    "Турция",
    "Польша",
    "Бразилия",
    "Канада",
    "Иран",
    "Израиль",
    "Саудовская Аравия",
    "Южная Корея",
]


def clean_text(text: Any) -> Any:
    if not isinstance(text, str):
        return text
    return text.encode("utf-8", "ignore").decode("utf-8")



def clean_data(value: Any) -> Any:
    if isinstance(value, dict):
        return {clean_text(k): clean_data(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean_data(item) for item in value]
    if isinstance(value, str):
        return clean_text(value)
    return value


class DB:
    def __init__(self, path: str):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        cur = self.conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS game_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            player_country TEXT NOT NULL,
            current_date TEXT NOT NULL,
            world_summary TEXT NOT NULL,
            turn_number INTEGER NOT NULL DEFAULT 1
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_date TEXT NOT NULL,
            event_type TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_date TEXT NOT NULL,
            sender TEXT NOT NULL,
            recipient TEXT NOT NULL,
            subject TEXT NOT NULL,
            content TEXT NOT NULL,
            is_incoming INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
        """)

        self.conn.commit()

    def game_exists(self) -> bool:
        cur = self.conn.cursor()
        cur.execute("SELECT 1 FROM game_state WHERE id = 1")
        return cur.fetchone() is not None

    def create_game(self, player_country: str):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM game_state")
        cur.execute("DELETE FROM events")
        cur.execute("DELETE FROM messages")

        initial_summary = (
            f"Мир на 1 января 2016 года. Игрок управляет страной: {player_country}. "
            "Глобальная обстановка напряжённая, но открытая для дипломатии, экономики, "
            "санкций, конфликтов, торговых соглашений, союзов, пропаганды, реформ и кризисов. "
            "Все события должны развиваться логично, последовательно и с учётом контекста."
        )

        cur.execute("""
        INSERT INTO game_state (id, player_country, current_date, world_summary, turn_number)
        VALUES (1, ?, ?, ?, 1)
        """, (clean_text(player_country), INITIAL_DATE, clean_text(initial_summary)))

        cur.execute("""
        INSERT INTO events (game_date, event_type, title, content, created_at)
        VALUES (?, ?, ?, ?, ?)
        """, (
            INITIAL_DATE,
            "system",
            "Начало кампании",
            clean_text(f"Игрок начал кампанию за страну «{player_country}»."),
            now_iso(),
        ))

        self.conn.commit()

    def get_state(self):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM game_state WHERE id = 1")
        row = cur.fetchone()
        if not row:
            raise RuntimeError("Игра не инициализирована")
        return {k: clean_text(v) if isinstance(v, str) else v for k, v in dict(row).items()}

    def update_state(self, current_date=None, world_summary=None, turn_number=None):
        state = self.get_state()

        current_date = current_date if current_date is not None else state["current_date"]
        world_summary = world_summary if world_summary is not None else state["world_summary"]
        turn_number = turn_number if turn_number is not None else state["turn_number"]

        cur = self.conn.cursor()
        cur.execute("""
        UPDATE game_state
        SET current_date = ?, world_summary = ?, turn_number = ?
        WHERE id = 1
        """, (clean_text(current_date), clean_text(world_summary), turn_number))
        self.conn.commit()

    def add_event(self, game_date: str, event_type: str, title: str, content: str):
        cur = self.conn.cursor()
        cur.execute("""
        INSERT INTO events (game_date, event_type, title, content, created_at)
        VALUES (?, ?, ?, ?, ?)
        """, (clean_text(game_date), clean_text(event_type), clean_text(title), clean_text(content), now_iso()))
        self.conn.commit()

    def get_recent_events(self, limit: int = 20):
        cur = self.conn.cursor()
        cur.execute("""
        SELECT * FROM events
        ORDER BY id DESC
        LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        result = []
        for row in rows:
            item = dict(row)
            result.append({k: clean_text(v) if isinstance(v, str) else v for k, v in item.items()})
        return result[::-1]

    def add_message(self, game_date: str, sender: str, recipient: str, subject: str, content: str, is_incoming: bool):
        cur = self.conn.cursor()
        cur.execute("""
        INSERT INTO messages (game_date, sender, recipient, subject, content, is_incoming, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            clean_text(game_date),
            clean_text(sender),
            clean_text(recipient),
            clean_text(subject),
            clean_text(content),
            int(is_incoming),
            now_iso(),
        ))
        self.conn.commit()

    def get_inbox(self, player_country: str, limit: int = 15):
        cur = self.conn.cursor()
        cur.execute("""
        SELECT * FROM messages
        WHERE recipient = ? AND is_incoming = 1
        ORDER BY id DESC
        LIMIT ?
        """, (clean_text(player_country), limit))
        rows = cur.fetchall()
        result = []
        for row in rows:
            item = dict(row)
            result.append({k: clean_text(v) if isinstance(v, str) else v for k, v in item.items()})
        return result

    def get_recent_messages(self, limit: int = 20):
        cur = self.conn.cursor()
        cur.execute("""
        SELECT * FROM messages
        ORDER BY id DESC
        LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        result = []
        for row in rows:
            item = dict(row)
            result.append({k: clean_text(v) if isinstance(v, str) else v for k, v in item.items()})
        return result[::-1]



def now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")



def advance_date(date_str: str, days: int = 7) -> str:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    dt += timedelta(days=days)
    return dt.strftime("%Y-%m-%d")


class DeepSeekEngine:
    def __init__(self, api_key: str, base_url: str, model: str):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.8,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content or "{}"
        content = clean_text(content)
        return clean_data(json.loads(content))



def build_context(db: DB, max_events: int = 12, max_messages: int = 10) -> str:
    state = db.get_state()
    events = db.get_recent_events(limit=max_events)
    messages = db.get_recent_messages(limit=max_messages)

    event_lines = []
    for e in events:
        event_lines.append(
            f"[{e['game_date']}] ({e['event_type']}) {e['title']}: {e['content']}"
        )

    message_lines = []
    for m in messages:
        direction = "IN" if m["is_incoming"] else "OUT"
        message_lines.append(
            f"[{m['game_date']}] [{direction}] {m['sender']} -> {m['recipient']} | {m['subject']}: {m['content']}"
        )

    context = f"""
Текущее состояние мира:
Дата: {state["current_date"]}
Ход: {state["turn_number"]}
Страна игрока: {state["player_country"]}

Сводка мира:
{state["world_summary"]}

Последние события:
{chr(10).join(event_lines) if event_lines else "Нет событий"}

Последние сообщения:
{chr(10).join(message_lines) if message_lines else "Нет сообщений"}
""".strip()

    return clean_text(context)


ACTION_SYSTEM_PROMPT = """
Ты — игровой движок политической CLI-стратегии.
Твоя задача: обработать действие игрока и вернуть обновление мира.

Правила:
1. Действие должно иметь последствия, но не всегда идеальные.
2. Учитывай реализм, дипломатию, экономику, общественное мнение, военные риски, пропаганду, санкции, внутреннюю политику.
3. Не ломай мир абсурдом. Реагируй правдоподобно.
4. Ответ строго в JSON.
5. Не пиши ничего вне JSON.

Формат JSON:
{
  "title": "короткий заголовок события",
  "result_text": "подробное описание результата действия",
  "world_summary_update": "краткая обновлённая сводка мира",
  "spawn_messages": [
    {
      "sender": "страна",
      "recipient": "страна игрока",
      "subject": "тема",
      "content": "текст сообщения"
    }
  ]
}
""".strip()


MESSAGE_SYSTEM_PROMPT = """
Ты — игровой движок дипломатической переписки в политической CLI-стратегии.

Твоя задача:
1. Получить исходящее сообщение игрока другой стране.
2. Сгенерировать логичную реакцию адресата.
3. Вернуть JSON.

Правила:
- Учитывай текущий мировой контекст.
- Ответ должен быть дипломатичным, реалистичным и связанным с ситуацией.
- Адресат может ответить положительно, отрицательно, уклончиво или с требованиями.
- Иногда сообщение игрока может спровоцировать новые события.

Формат JSON:
{
  "reply_subject": "тема ответа",
  "reply_content": "текст ответа страны",
  "event_title": "краткий заголовок дипломатического последствия",
  "event_text": "что изменилось в мире после переписки",
  "world_summary_update": "краткая обновлённая сводка мира"
}
""".strip()


ADVANCE_SYSTEM_PROMPT = """
Ты — игровой движок глобальных событий в политической CLI-стратегии.

Твоя задача:
- продвинуть мир на следующий ход без активного действия игрока;
- сгенерировать 1-3 разумных события;
- возможно, создать 0-2 входящих сообщения игроку;
- обновить краткую сводку мира.

Ответ строго в JSON.

Формат JSON:
{
  "events": [
    {
      "title": "заголовок события",
      "content": "описание события"
    }
  ],
  "spawn_messages": [
    {
      "sender": "страна",
      "recipient": "страна игрока",
      "subject": "тема",
      "content": "текст"
    }
  ],
  "world_summary_update": "новая краткая сводка мира"
}
""".strip()



def apply_action(db: DB, ai: DeepSeekEngine, action_text: str):
    state = db.get_state()
    context = build_context(db)

    prompt = f"""
Игрок управляет страной: {state["player_country"]}

Контекст:
{context}

Действие игрока:
{action_text}
""".strip()

    data = ai.complete_json(ACTION_SYSTEM_PROMPT, prompt)

    title = clean_text(data.get("title", "Последствия действия"))
    result_text = clean_text(data.get("result_text", "Мир отреагировал на действие игрока."))
    summary = clean_text(data.get("world_summary_update", state["world_summary"]))
    spawn_messages = clean_data(data.get("spawn_messages", []))

    db.add_event(
        game_date=state["current_date"],
        event_type="action_result",
        title=title,
        content=result_text,
    )

    for msg in spawn_messages:
        sender = clean_text(msg.get("sender", "Неизвестная страна"))
        recipient = clean_text(msg.get("recipient", state["player_country"]))
        subject = clean_text(msg.get("subject", "Без темы"))
        content = clean_text(msg.get("content", ""))
        db.add_message(
            game_date=state["current_date"],
            sender=sender,
            recipient=recipient,
            subject=subject,
            content=content,
            is_incoming=True,
        )

    db.update_state(
        world_summary=summary,
        turn_number=state["turn_number"] + 1,
    )

    print("\n=== РЕЗУЛЬТАТ ДЕЙСТВИЯ ===")
    print(title)
    print(result_text)

    if spawn_messages:
        print("\n=== НОВЫЕ СООБЩЕНИЯ ===")
        for msg in spawn_messages:
            print(f"{clean_text(msg.get('sender', '???'))} | {clean_text(msg.get('subject', 'Без темы'))}")
            print(clean_text(msg.get("content", "")))
            print("-" * 50)



def send_message(db: DB, ai: DeepSeekEngine, recipient: str, subject: str, content: str):
    state = db.get_state()
    player_country = state["player_country"]

    db.add_message(
        game_date=state["current_date"],
        sender=player_country,
        recipient=recipient,
        subject=subject,
        content=content,
        is_incoming=False,
    )

    context = build_context(db)

    prompt = f"""
Контекст:
{context}

Игрок ({player_country}) отправил сообщение стране {recipient}.

Тема:
{subject}

Текст:
{content}
""".strip()

    data = ai.complete_json(MESSAGE_SYSTEM_PROMPT, prompt)

    reply_subject = clean_text(data.get("reply_subject", f"Re: {subject}"))
    reply_content = clean_text(data.get("reply_content", "Мы приняли ваше сообщение к сведению."))
    event_title = clean_text(data.get("event_title", "Дипломатическая переписка"))
    event_text = clean_text(data.get("event_text", "Переписка повлияла на международную обстановку."))
    summary = clean_text(data.get("world_summary_update", state["world_summary"]))

    db.add_message(
        game_date=state["current_date"],
        sender=recipient,
        recipient=player_country,
        subject=reply_subject,
        content=reply_content,
        is_incoming=True,
    )

    db.add_event(
        game_date=state["current_date"],
        event_type="diplomacy",
        title=event_title,
        content=event_text,
    )

    db.update_state(
        world_summary=summary,
        turn_number=state["turn_number"] + 1,
    )

    print("\n=== ОТВЕТ ПОЛУЧЕН ===")
    print(f"{clean_text(recipient)} | {reply_subject}")
    print(reply_content)
    print("\n=== ПОСЛЕДСТВИЯ ===")
    print(event_title)
    print(event_text)



def next_turn(db: DB, ai: DeepSeekEngine):
    state = db.get_state()
    next_date = advance_date(state["current_date"], days=7)
    context = build_context(db)

    prompt = f"""
Продвинь мир с даты {state["current_date"]} до {next_date}.

Контекст:
{context}
""".strip()

    data = ai.complete_json(ADVANCE_SYSTEM_PROMPT, prompt)

    events = clean_data(data.get("events", []))
    spawn_messages = clean_data(data.get("spawn_messages", []))
    summary = clean_text(data.get("world_summary_update", state["world_summary"]))

    db.update_state(
        current_date=next_date,
        world_summary=summary,
        turn_number=state["turn_number"] + 1,
    )

    if not events:
        events = [{
            "title": "Относительно спокойная неделя",
            "content": "Крупных потрясений не произошло, но напряжение в мире сохраняется."
        }]

    for event in events:
        db.add_event(
            game_date=next_date,
            event_type="world_event",
            title=clean_text(event.get("title", "Мировое событие")),
            content=clean_text(event.get("content", "")),
        )

    player_country = state["player_country"]
    for msg in spawn_messages:
        db.add_message(
            game_date=next_date,
            sender=clean_text(msg.get("sender", "Неизвестная страна")),
            recipient=clean_text(msg.get("recipient", player_country)),
            subject=clean_text(msg.get("subject", "Без темы")),
            content=clean_text(msg.get("content", "")),
            is_incoming=True,
        )

    print(f"\n=== СЛЕДУЮЩИЙ ХОД: {next_date} ===")
    for event in events:
        print(f"- {clean_text(event.get('title', 'Событие'))}")
        print(f"  {clean_text(event.get('content', ''))}")

    if spawn_messages:
        print("\n=== ВХОДЯЩИЕ ===")
        for msg in spawn_messages:
            print(f"{clean_text(msg.get('sender', '???'))} | {clean_text(msg.get('subject', 'Без темы'))}")
            print(clean_text(msg.get("content", "")))
            print("-" * 50)



def show_status(db: DB):
    state = db.get_state()
    print("\n=== СТАТУС ===")
    print(f"Страна: {state['player_country']}")
    print(f"Дата: {state['current_date']}")
    print(f"Ход: {state['turn_number']}")
    print("\nСводка мира:")
    print(clean_text(state["world_summary"]))



def show_events(db: DB, limit: int = 10):
    events = db.get_recent_events(limit=limit)
    print("\n=== ПОСЛЕДНИЕ СОБЫТИЯ ===")
    if not events:
        print("Нет событий.")
        return

    for e in reversed(events):
        print(f"[{e['game_date']}] {clean_text(e['title'])}")
        print(shorten(clean_text(e["content"]), width=220, placeholder="..."))
        print("-" * 50)



def show_inbox(db: DB):
    state = db.get_state()
    inbox = db.get_inbox(state["player_country"], limit=15)

    print("\n=== ВХОДЯЩИЕ СООБЩЕНИЯ ===")
    if not inbox:
        print("Пока пусто.")
        return

    for m in reversed(inbox):
        print(f"[{m['game_date']}] {clean_text(m['sender'])} -> {clean_text(m['recipient'])}")
        print(f"Тема: {clean_text(m['subject'])}")
        print(clean_text(m["content"]))
        print("-" * 50)



def select_country() -> str:
    print("Выбери страну:")
    for i, country in enumerate(AVAILABLE_COUNTRIES, start=1):
        print(f"{i}. {country}")

    while True:
        choice = input("\nНомер страны: ").strip()
        if not choice.isdigit():
            print("Введи номер.")
            continue

        idx = int(choice)
        if 1 <= idx <= len(AVAILABLE_COUNTRIES):
            return AVAILABLE_COUNTRIES[idx - 1]

        print("Такой страны в списке нет.")



def show_help():
    print("""
Доступные команды:
1. action       — совершить действие
2. message      — отправить сообщение стране
3. inbox        — посмотреть входящие
4. events       — посмотреть последние события
5. status       — текущая сводка мира
6. next         — перейти к следующему ходу
7. help         — показать помощь
8. quit         — выйти
""".strip())



def input_multiline(prompt: str) -> str:
    print(prompt)
    print("Закончи ввод пустой строкой.")
    lines = []
    while True:
        line = input("> ")
        if line == "":
            break
        lines.append(line)
    return clean_text("\n".join(lines).strip())



def main():
    db = DB(DB_PATH)
    ai = DeepSeekEngine(
        api_key=API_KEY,
        base_url=DEFAULT_BASE_URL,
        model=DEFAULT_MODEL,
    )

    print("=== GEO-CLI 2016 ===")

    if not db.game_exists():
        player_country = select_country()
        db.create_game(player_country)
        print(f"\nИгра создана. Ты управляешь страной: {player_country}")
        print("Стартовая дата: 2016-01-01")
    else:
        state = db.get_state()
        print(f"Загружена существующая игра. Страна: {state['player_country']}, дата: {state['current_date']}")

    show_help()

    while True:
        cmd = input("\nКоманда: ").strip().lower()

        try:
            if cmd == "action":
                text = input_multiline("Опиши действие:")
                if not text:
                    print("Пустое действие отменено.")
                    continue
                apply_action(db, ai, text)

            elif cmd == "message":
                recipient = clean_text(input("Кому: ").strip())
                if not recipient:
                    print("Нужно указать страну.")
                    continue

                if recipient not in WORLD_COUNTRIES:
                    print("Неизвестная страна. Но можешь всё равно использовать реальное название при желании.")
                subject = clean_text(input("Тема: ").strip()) or "Без темы"
                content = input_multiline("Текст сообщения:")
                if not content:
                    print("Пустое сообщение отменено.")
                    continue
                send_message(db, ai, recipient, subject, content)

            elif cmd == "inbox":
                show_inbox(db)

            elif cmd == "events":
                show_events(db)

            elif cmd == "status":
                show_status(db)

            elif cmd == "next":
                next_turn(db, ai)

            elif cmd == "help":
                show_help()

            elif cmd == "quit":
                print("Выход из игры.")
                break

            else:
                print("Неизвестная команда. Введи help.")

        except KeyboardInterrupt:
            print("\nДействие прервано.")
        except Exception as e:
            print(f"\nОшибка: {clean_text(str(e))}")


if __name__ == "__main__":
    main()
