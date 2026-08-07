from pathlib import Path

from alembic.config import Config
from pytest import CaptureFixture

from alembic import command


def migration_config() -> Config:
    api_root = Path(__file__).resolve().parents[1]
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("script_location", str(api_root / "alembic"))
    return config


def test_migration_upgrade_and_downgrade_render_postgresql_sql(
    capsys: CaptureFixture[str],
) -> None:
    command.upgrade(migration_config(), "head", sql=True)
    upgrade_sql = capsys.readouterr().out
    assert "CREATE TYPE repository_status" in upgrade_sql
    assert "CREATE TABLE repositories" in upgrade_sql
    assert "CREATE TABLE analysis_jobs" in upgrade_sql
    assert "CREATE TABLE analysis_stages" in upgrade_sql
    assert "CREATE TABLE repository_files" in upgrade_sql
    assert "CREATE TABLE code_chunks" in upgrade_sql
    assert "CREATE TABLE code_findings" in upgrade_sql
    assert upgrade_sql.count("CREATE TYPE finding_severity") == 1
    assert upgrade_sql.count("CREATE TYPE finding_category") == 1
    assert "ON DELETE RESTRICT" in upgrade_sql

    command.downgrade(migration_config(), "head:base", sql=True)
    downgrade_sql = capsys.readouterr().out
    assert "DROP TABLE analysis_stages" in downgrade_sql
    assert "DROP TABLE code_chunks" in downgrade_sql
    assert "DROP TABLE repository_files" in downgrade_sql
    assert "DROP TABLE analysis_jobs" in downgrade_sql
    assert "DROP TABLE repositories" in downgrade_sql
    assert "DROP TYPE repository_status" in downgrade_sql
