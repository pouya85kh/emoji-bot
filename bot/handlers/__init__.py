from bot.handlers import (
    account,
    admin,
    channels,
    extract,
    help,
    inline,
    my_emojis,
    premium,
    start,
    support,
)

routers = (
    start.router,
    account.router,
    premium.router,
    inline.router,
    extract.router,
    my_emojis.router,
    channels.router,
    help.router,
    support.router,
    admin.router,
)
