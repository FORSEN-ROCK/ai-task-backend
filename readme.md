# AI Task Planner

## Локальный запуск

Для локальной разработки нужны Docker Compose, Python 3.12 и `uv`.
Все команды выполняются из корня репозитория.

### PostgreSQL и Keycloak

Поднимите сервисы и проверьте их состояние:

```bash
docker compose -f dev/compose.yaml up -d
docker compose -f dev/compose.yaml ps
```

По умолчанию админ-консоль Keycloak доступна на
[порту 8080](http://127.0.0.1:8080/admin/), а PostgreSQL — на
`127.0.0.1:5433`. Порты можно переопределить переменными
`KEYCLOAK_PORT` и `POSTGRES_PORT`.

Для локальной разработки Keycloak использует `admin / admin-dev`, PostgreSQL —
`planner / planner-dev`. При первом запуске PostgreSQL создаёт базы
`ai_task_planner` и `keycloak`.

### FastAPI

Скопируйте шаблон в `.env` и заполните значения для PostgreSQL и Keycloak.
FastAPI читает `.env` из корня проекта при старте. Переменные окружения
имеют приоритет над значениями из файла.

```bash
cp -n env.template .env
uv sync --locked
.venv/bin/uvicorn app.main:app --reload
```

- [Swagger UI](http://127.0.0.1:8000/docs)
- [OpenAPI JSON](http://127.0.0.1:8000/openapi.json)
- [Проверка состояния приложения](http://127.0.0.1:8000/health)

Текущий маршрут проверки состояния доступен без подключения к PostgreSQL и Keycloak.

Для проверки токенов создайте в выбранном realm конфиденциальный OIDC-клиент.
Укажите его ID и секрет в `KEYCLOAK__CLIENT_ID` и `KEYCLOAK__CLIENT_SECRET`.
Настройте Audience mapper, чтобы ID этого клиента присутствовал в `aud`
access-токенов, и включите клиентские и realm-роли в ответ introspection.

Для регистрации создайте отдельный конфиденциальный клиент с включёнными
service accounts и назначьте его сервисной учётной записи роль
`realm-management/manage-users`. В Keycloak 26.8 добавьте клиенту
`kc-admin-api` как Default client scope. Укажите данные клиента в
`KEYCLOAK__ADMIN_CLIENT_ID` и `KEYCLOAK__ADMIN_CLIENT_SECRET`.

Для входа по логину и паролю включите **Direct access grants** у OIDC-клиента,
указанного в `KEYCLOAK__CLIENT_ID`. Маршруты принимают JSON:

- `POST /auth/register` принимает `username`, `email` и `password`.
  Передайте также `first_name` и `last_name`, чтобы пользователь мог сразу
  войти со стандартными настройками профиля Keycloak. При успехе маршрут
  возвращает `201 Created`.
- `POST /auth/login` принимает `username` и `password`.
- `POST /auth/refresh` принимает `refresh_token`.
- `POST /auth/logout` принимает `refresh_token`, завершает сессию
  и возвращает `204 No Content`.

Вход и обновление возвращают `access_token` и, если они доступны,
`refresh_token`, `token_type` и `expires_in` в секундах. Ошибки API
возвращаются в поле `detail`.

Защищённые маршруты принимают `Authorization: Bearer <access_token>`.
Проверенный пользователь доступен в `request.state.user`. При отсутствии
действительного токена API возвращает `401`, при недоступности сервиса
аутентификации — `503`. Маршруты `/health`, документация и публичные
операции `/auth` доступны без токена.

## Alembic

Alembic использует параметры `DATABASE__*` из того же `.env`, что и приложение.
Для проверки списка ревизий из корня проекта выполните:

```bash
.venv/bin/alembic history
```

Чтобы создать таблицы пользователей и планирования, запустите PostgreSQL
и примените ревизии:

```bash
.venv/bin/alembic upgrade head
```

## API планирования

С токеном доступа доступны коллекции `/planning/goals`, `/planning/tasks`,
`/planning/factors` и `/planning/task-dependencies`. Для каждой коллекции
`GET` возвращает список, а `POST` создаёт запись. По пути с UUID записи
доступны `GET`, `PUT` для полной замены и `DELETE`.

Приоритет цели и задачи задаётся от 1 до 5, где 5 — наивысший. Доступное
время цели измеряется в минутах, срок задаётся датой, период влияния фактора
измеряется в днях. Факторы принадлежат пользователю. Связь направлена от
левой задачи к правой и может соединять задачи разных целей одного владельца.

При удалении цели PostgreSQL удаляет её задачи и все связи, в которых они
участвуют. Задачи других целей и факторы пользователя сохраняются.

Чтобы остановить сервисы и сохранить данные PostgreSQL:

```bash
docker compose -f dev/compose.yaml down
```

## Сборка и запуск Docker-образа

Из корня репозитория выполните:

```bash
docker build -f build/Dockerfile -t ai-task-planner:local .
docker run --rm --env-file .env -p 127.0.0.1:8000:8000 ai-task-planner:local
```

Swagger UI доступен по адресу [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).
Для обращения к PostgreSQL и Keycloak из контейнера укажите в переменных
окружения адреса, доступные из контейнера. Адрес `127.0.0.1` внутри него
указывает на сам контейнер.

## Полный стек в Docker Compose

Из корня проекта выполните:

```bash
python3 build/generate_env.py
docker compose --env-file build/.env -f build/compose.yaml up --build -d
docker compose --env-file build/.env -f build/compose.yaml ps -a
```

Генератор создаёт `build/.env` со случайными паролями и секретами
с правами `0600`. Повторный запуск сохраняет существующий файл.
Храните его вместе с резервной копией данных. PostgreSQL создаёт
отдельные базы и роли на пустом томе, а Keycloak импортирует realm
`planner` с клиентами для входа и регистрации. Перед стартом FastAPI
сервис `migrate` применяет миграции Alembic и завершается.

- [Swagger UI](http://127.0.0.1:8000/docs), порт задаётся через `APP_PORT`.
- [Консоль Keycloak](http://localhost:8080/admin/), порт задаётся через
  `KEYCLOAK_PORT`. Имя администратора — `admin`, пароль хранится в
  `KEYCLOAK_ADMIN_PASSWORD` в `build/.env`.

Чтобы остановить стек и сохранить данные:

```bash
docker compose --env-file build/.env -f build/compose.yaml down
```

## Проверки перед коммитом

После клонирования репозитория включите Git-хуки:

```bash
git config --local core.hooksPath .githooks
```

Перед коммитом хук проверяет код и форматирование через Ruff, затем запускает
pytest. Если какая-либо проверка завершается с ошибкой, Git прерывает коммит.
