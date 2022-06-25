"""Creates and configures some variables of .env"""

import header

if __name__ == "__main__":
    with open(".env", "r") as file:
        txt = file.read()
    file = open(".env", "w")
    try:
        print("You can either manually edit .env later or input them now. Quit with ctrl + c")
        txt = txt.replace("BOT_TOKEN=", "BOT_TOKEN=" + input("bot token: "))
        print("The next options are %s, leave empty for default value" % header.fg.y("optional"))
        if i := input("bot prefix: "):
            txt = txt.replace("BOT_PREFIX=,,", "BOT_PREFIX="+i)
        print("Valid levels: debug, info, warning, error, critical")
        if i := input("Logging level: "):
            txt = txt.replace("BOT_LOG_LEVEL=info", "BOT_LOG_LEVEL="+i)
        if i := input("Postgres database ssl url: "):
            txt = txt.replace("# DATABASE_URL=", "DATABASE_URL="+i)
        file.write(txt)
        input(header.fg.G(".env has been successfully updated!\n"))
    except KeyboardInterrupt:
        pass
    finally:
        file.close()
