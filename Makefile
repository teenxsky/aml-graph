ENV_FILE = ./.env
COMPOSE_FILE = ./docker-compose.yaml
COMPOSE = docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE)

# Если DOCKER=1, то работаем через docker compose
ifeq ($(DOCKER),1)
	BACKEND_CMD = $(COMPOSE) exec backend uv run
	FRONTEND_CMD = $(COMPOSE) exec frontend
else
	BACKEND_CMD = cd backend && uv run
	FRONTEND_CMD = cd frontend &&
endif


.PHONY: help
help:
	@echo "\033[33mДоступные команды:\033[0m"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'


#--------------- ОСНОВНЫЕ КОМАНДЫ ---------------#

.PHONY: env
env: ## Скопировать .env.example в .env
	@cp .env.example .env

.PHONY: build
build: ## Собрать Docker-образы
	@$(COMPOSE) up -d --build

.PHONY: up
up: ## Запустить все Docker-контейнеры
	@$(COMPOSE) up -d --remove-orphans

.PHONY: up-backend
up-backend: ## Запустить backend Docker-контейнер
	@$(COMPOSE) up -d --remove-orphans backend

.PHONY: up-frontend
up-frontend: ## Запустить frontend Docker-контейнер
	@$(COMPOSE) up -d --remove-orphans frontend

.PHONY: down
down: ## Остановить Docker-контейнеры
	@$(COMPOSE) down

.PHONY: clean
clean: ## Очистить окружение (удалить образы)
	@$(COMPOSE) down --rmi all

.PHONY: clean-volumes
clean-volumes: ## Очистить окружение (удалить тома)
	@$(COMPOSE) down -v

.PHONY: restart
restart: ## Перезапустить Docker-контейнеры
	@$(COMPOSE) restart

#--------------- КОМАНДЫ ПРИЛОЖЕНИЯ ---------------#

.PHONY: install-backend
install-backend: ## Установить backend зависимости
	@$(BACKEND_CMD) uv sync

.PHONY: install-frontend
install-frontend: ## Установить frontend зависимости
	@$(FRONTEND_CMD) npm ci

.PHONY: run-backend-tests
run-backend-tests: ## Запустить тесты backend
	@$(BACKEND_CMD) uv run python -m pytest

.PHONY: generate-migration
generate-migration: ## Сгенерировать миграцию на основе актуальных моделей
	@$(BACKEND_CMD) sh -c 'read -p "Введите сообщение миграции: " message && \
					alembic revision --autogenerate -m "$$message"'

.PHONY: create-migration
create-migration: ## Создать чистую (пустую) миграцию
	@$(BACKEND_CMD) sh -c 'read -p "Введите сообщение миграции: " message && \
					alembic revision -m "$$message"'

.PHONY: migrate
migrate: ## Запустить процесс миграции БД
	@$(BACKEND_CMD) alembic upgrade head


#--------------- КОМАНДЫ ДЛЯ КОД-СТИЛЯ ---------------#

.PHONY: install-pre-commit
install-pre-commit: ## Установить pre-commit хуки
	@pre-commit install

.PHONY: run-pre-commit
run-pre-commit: ## Запустить pre-commit проверки
	@pre-commit run -a

.PHONY: ty-check
ty-check: ## Проверить типизацию кода с помощью TY
	@$(BACKEND_CMD) ty check

.PHONY: ruff-check
ruff-check: ## Проверить стиль backend кода (линтинг) с помощью Ruff
	@$(BACKEND_CMD) ruff check . --config=ruff.toml

.PHONY: ruff-fix
ruff-fix: ## Исправить ошибки стиля с помощью Ruff
	@$(BACKEND_CMD) ruff check . --fix --unsafe-fixes --config=ruff.toml

.PHONY: prettier-check
prettier-check: ## Проверить стиль frontend кода
	@$(FRONTEND_CMD) npm run prettier-check

.PHONY: prettier-fix
prettier-fix: ## Исправить стиль frontend кода
	@$(FRONTEND_CMD) npm run prettier-fix

.PHONY: eslint-check
eslint-check: ## Проверить типизацию frontend кода с помощью Eslint
	@$(FRONTEND_CMD) npm run eslint-check

.PHONY: eslint-fix
eslint-fix: ## Исправить ошибки типизации frontend кода с помощью Eslint
	@$(FRONTEND_CMD) npm run eslint-fix
