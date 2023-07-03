from sp_vk.bot import bot
from sp_vk.middleware import SpMiddleware


if __name__ == "__main__":
    bot.labeler.message_view.register_middleware(SpMiddleware)
    bot.run_forever()