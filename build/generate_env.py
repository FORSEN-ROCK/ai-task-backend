import argparse
import os
from pathlib import Path
from secrets import token_urlsafe

SECRET_NAMES = (
    "POSTGRES_ADMIN_PASSWORD",
    "PLANNER_DB_PASSWORD",
    "KEYCLOAK_DB_PASSWORD",
    "KEYCLOAK_ADMIN_PASSWORD",
    "PLANNER_CLIENT_SECRET",
    "PLANNER_ADMIN_CLIENT_SECRET",
)


def main() -> None:
    """Создаёт файл окружения Compose со случайными секретами."""
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name(".env"))
    output = parser.parse_args().output
    try:
        descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        print(f"Используется существующий файл {output}")
        return

    with os.fdopen(descriptor, "w", encoding="utf-8") as env_file:
        env_file.write("APP_PORT=8000\nKEYCLOAK_PORT=8080\n")
        for name in SECRET_NAMES:
            env_file.write(f"{name}={token_urlsafe(32)}\n")
    print(f"Создан файл {output}")


if __name__ == "__main__":
    main()
