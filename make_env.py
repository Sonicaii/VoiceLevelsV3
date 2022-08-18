#!/usr/bin/env python3
"""Creates and configures some variables of .env"""

import header

# pylint: disable=no-member
if __name__ == "__main__":
    with open(".env", "r", encoding="utf-8") as file:
        txt = file.read()
    with open(".env", "w", encoding="utf-8") as file:
        print("You can either manually edit .env later or input them now. Quit with ctrl + c")
        txt = txt.replace("BOT_TOKEN=", "BOT_TOKEN=" + input("bot token: "))
        print(f"The next options are {header.fg.y('optional')}, leave empty for default value")
        if i := input("bot prefix: "):
            txt = txt.replace("BOT_PREFIX=,,", "BOT_PREFIX="+i)
        print("Valid levels: debug, info, warning, error, critical")
        if i := input("Logging level: "):
            txt = txt.replace("BOT_LOG_LEVEL=info", "BOT_LOG_LEVEL="+i)
        if i := input("Postgres database ssl url: "):
            txt = txt.replace("# DATABASE_URL=", "DATABASE_URL="+i)
        file.write(txt)
        input(header.fg.G(".env has been successfully updated!\n"))
