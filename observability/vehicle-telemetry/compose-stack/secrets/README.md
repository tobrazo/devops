Drop the Alertmanager Telegram bot token here as a file named `telegram-token`:

    printf '%s' '123456:ABC-your-token' > telegram-token

Alertmanager reads it via `bot_token_file` — it does **not** expand environment
variables in its config, so `${TELEGRAM_BOT_TOKEN}` there would be sent to
Telegram verbatim.

The token file is gitignored. Only this README and .gitkeep are committed.
