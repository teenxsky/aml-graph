from dishka import AsyncContainer, make_async_container


def create_container() -> AsyncContainer:
    """
    Создаёт и настраивает IoC-контейнер dishka.

    :return: Сконфигурированный AsyncContainer со всеми зарегистрированными провайдерами.
    """
    return make_async_container()
