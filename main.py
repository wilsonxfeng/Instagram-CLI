import os
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv
from instagrapi import Client
from instagrapi.exceptions import ClientError, ClientLoginRequired

SESSION_PATH = Path("session.json")
THREAD_MESSAGE_LIMIT = 10


def login_with_session(cl: Client, username: str, password: str) -> None:
    if SESSION_PATH.exists():
        cl.load_settings(SESSION_PATH)
    try:
        cl.login(username, password)
    except (ClientLoginRequired, ClientError):
        if SESSION_PATH.exists():
            SESSION_PATH.unlink()
        cl.login(username, password)
        cl.dump_settings(SESSION_PATH)


def fetch_threads(cl: Client, amount: int = 10):
    return cl.direct_threads(amount=amount, thread_message_limit=THREAD_MESSAGE_LIMIT)


def format_thread_title(thread) -> str:
    if thread.thread_title:
        return thread.thread_title
    return ", ".join(u.username for u in thread.users)


def list_inbox(cl: Client, amount: int = 10):
    threads = fetch_threads(cl, amount=amount)
    for i, t in enumerate(threads, start=1):
        last = t.messages[0] if t.messages else None
        last_text = last.text if last and last.text else ""
        print(f"[{i}] {format_thread_title(t)} {last_text}")
    return threads


def build_user_lookup(thread) -> Dict[str, str]:
    return {str(u.pk): u.username for u in thread.users}


def print_messages(
    cl: Client,
    thread_id: str,
    amount: int = 20,
    users: Optional[Dict[str, str]] = None,
):
    msgs = cl.direct_messages(thread_id, amount=amount)
    users = users or {}
    for m in sorted(msgs, key=lambda x: x.timestamp):
        sender = users.get(
            str(m.user_id),
            "me" if str(m.user_id) == str(cl.user_id) else str(m.user_id),
        )
        text = m.text or ""
        print(f"{m.timestamp} {sender}: {text}")


def repl(cl: Client):
    threads_cache: List = []
    current_thread: Optional = None
    current_users: Dict[str, str] = {}
    print("Type 'help' for commands.")
    while True:
        if current_thread:
            prompt = f"ig/{format_thread_title(current_thread)}/> "
        else:
            prompt = "ig/> "
        cmd = input(prompt).strip()
        if not cmd:
            continue
        if cmd in {"quit", "exit"}:
            break
        if cmd == "help":
            print("inbox [n] | open <index> | read [n] | send <message> | back | quit")
            continue
        if cmd.startswith("inbox") or cmd.startswith("ls"):
            parts = cmd.split()
            amount = int(parts[1]) if len(parts) > 1 else 10
            threads_cache = list_inbox(cl, amount=amount)
            continue
        if cmd.startswith("open") or cmd.startswith("cd"):
            parts = cmd.split()
            if len(parts) != 2 or not parts[1].isdigit():
                print("usage: open <index>")
                continue
            idx = int(parts[1]) - 1
            if idx < 0 or idx >= len(threads_cache):
                print("invalid index")
                continue
            current_thread = threads_cache[idx]
            current_users = build_user_lookup(current_thread)
            print(f"opened: {format_thread_title(current_thread)}")
            continue
        if cmd.startswith("read"):
            if not current_thread:
                print("open a thread first")
                continue
            parts = cmd.split()
            amount = int(parts[1]) if len(parts) > 1 else 20
            print_messages(cl, current_thread.id, amount=amount, users=current_users)
            continue
        if cmd.startswith("send "):
            if not current_thread:
                print("open a thread first")
                continue
            message = cmd[len("send ") :].strip()
            if not message:
                print("usage: send <message>")
                continue
            cl.direct_answer(current_thread.id, message)
            print("sent")
            continue
        if cmd == "back":
            current_thread = None
            current_users = {}
            print("thread cleared")
            continue
        print("unknown command. type 'help'")


def main():
    load_dotenv()

    account_username = os.environ["USERNAME"]
    account_password = os.environ["PASSWORD"]

    cl = Client()
    login_with_session(cl, account_username, account_password)
    repl(cl)


if __name__ == "__main__":
    main()
