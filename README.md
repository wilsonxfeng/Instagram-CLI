# IGCLI

Tiny REPL for Instagram DMs in your terminal.

## Requirements
- Python 3.13
- An Instagram account

## Setup
```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file:
```env
USERNAME=your_username
PASSWORD=your_password
```

## Run
```bash
python main.py
```

## Web UI
```bash
python app.py
```
Open `http://127.0.0.1:5000` in a browser.

## Commands
- `inbox [n]`
- `open <index>`
- `read [n]`
- `send <message>`
- `back`
- `quit`

## Notes
- A `session.json` file is created after first login and reused on later runs.
