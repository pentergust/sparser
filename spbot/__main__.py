from spbot.bot import runner

from loguru import logger


# Запуск скрипта
# ==============

if __name__ == "__main__":
    logger.add("sp_data/telegram.log")
    runner.skip_updates = True
    runner.start_polling()
