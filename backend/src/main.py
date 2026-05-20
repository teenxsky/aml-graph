import time

import uvicorn

from src.logging import get_logging_config, setup_logger
from src.settings import settings

if __name__ == '__main__':
    """Запуск приложения."""
    time.tzset()
    setup_logger()

    uvicorn.run(
        app='src.app:app',
        loop='uvloop',
        host=settings.app.host,
        port=settings.app.port,
        reload=settings.app.debug,
        log_config=get_logging_config(),
    )
