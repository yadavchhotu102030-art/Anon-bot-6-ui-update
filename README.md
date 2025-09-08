# AnonChat — UI-First Template

## Overview
This repository contains a clean UI-fronted anonymous Telegram chat bot. Surveillance and monitoring logic is intentionally isolated in `surveillance.py` so that government/crime-bureau integrations can remain untouched.

## Files
- `bot.py` : Main bot (polling). Uses `ui.py` and `surveillance.py`.
- `ui.py` : UI messages and inline keyboard templates.
- `surveillance.py` : Monitoring hooks. **Replace** with your actual surveillance code if needed.
- `web.py` : Optional webhook skeleton (Flask).
- `requirements.txt`

## Setup
1. Create a Python 3.10+ virtualenv.
2. Install: `pip install -r requirements.txt`.
3. Create a `.env` or set environment variables:
   - `BOT_TOKEN`
   - `ADMIN_IDS` (comma-separated)
   - `SPECTATOR_GROUP_ID` (telegram group id where supervisors watch)
4. If you have an existing surveillance module, copy its contents into `surveillance.py` (keep function names used in `bot.py`).
5. Run bot: `python bot.py`.

## Important
- Do *not* edit the `surveillance.py` calls in `bot.py`. If you have an existing, functioning surveillance module, place it in `surveillance.py` so calls continue to operate unchanged.
- UI is modular in `ui.py`. Edit text/buttons there.
- 
