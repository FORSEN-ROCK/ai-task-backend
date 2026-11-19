# AI Task Planner

## Локальный запуск

Из корня репозитория с Python 3.12 и установленным `uv` выполните:

```bash
uv sync --locked
.venv/bin/uvicorn app.main:app --reload
```

- [Swagger UI](http://127.0.0.1:8000/docs)
- [OpenAPI JSON](http://127.0.0.1:8000/openapi.json)
- [Проверка состояния приложения](http://127.0.0.1:8000/health)

## Проверки перед коммитом

После клонирования репозитория включите Git-хуки:

```bash
git config --local core.hooksPath .githooks
```

Перед коммитом хук проверяет код и форматирование через Ruff, затем запускает
pytest. Если какая-либо проверка завершается с ошибкой, Git прерывает коммит.
