from uuid import UUID

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app.user import models, schemas

USER_ID = UUID("00112233-4455-6677-8899-aabbccddeeff")


def test_local_user_schemas_read_sqlalchemy_models() -> None:
    profile = models.UserProfile(user_id=USER_ID, preferences={"locale": "ru"})
    characteristics = models.UserCharacteristics(
        user_id=USER_ID,
        minor_goal="Подготовить черновик",
        major_goal="Завершить проект",
        completed_subtasks=["Собрать требования"],
        initiative="Предложить план",
    )

    assert schemas.UserProfile.model_validate(profile).preferences == {"locale": "ru"}
    result = schemas.UserCharacteristics.model_validate(characteristics)
    assert result.user_id == USER_ID
    assert result.completed_subtasks == ["Собрать требования"]
    assert result.major_goal == "Завершить проект"


def test_postgres_characteristics_reference_profile() -> None:
    profile = models.UserProfile.__table__
    characteristics = models.UserCharacteristics.__table__
    assert profile.name == "user_profiles"
    assert list(characteristics.primary_key.columns.keys()) == ["user_id"]

    ddl = str(CreateTable(characteristics).compile(dialect=postgresql.dialect()))
    assert "completed_subtasks JSONB" in ddl
    assert "REFERENCES user_profiles (user_id) ON DELETE CASCADE" in ddl
