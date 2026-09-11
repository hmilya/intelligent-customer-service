"""数据库连接串的驱动探测：缺包 / 同步驱动 / 厂商方言 / 格式错误都要给出可执行指引。

这些用例不连任何数据库，只验证建引擎前的那道「驱动体检」。
"""
from __future__ import annotations

import importlib.util

import pytest

from src.core.db_drivers import DatabaseDriverError, ensure_driver


# ── 正常路径：驱动在，就放行 ─────────────────────────────

@pytest.mark.parametrize("url", [
    "sqlite+aiosqlite:///./data/app.db",
    "mysql+aiomysql://u:p@localhost:3306/cs",
    # PG 及走 PG 协议的信创库共用 asyncpg
    "postgresql+asyncpg://u:p@localhost:5432/cs",
    "postgresql+asyncpg://system:pass@kingbase:54321/security",   # KingbaseES PG 模式
    "postgresql+asyncpg://u:p@opengauss:5432/cs",
])
def test_installed_drivers_pass(url):
    parsed = ensure_driver(url)
    assert parsed.get_backend_name() in {"sqlite", "mysql", "postgresql"}


# ── 同步驱动要拦下：装包救不了，必须改连接串 ───────────────

@pytest.mark.parametrize("url,keyword", [
    ("postgresql+psycopg2://u:p@localhost/cs", "postgresql\+asyncpg"),
    ("mysql+pymysql://u:p@localhost/cs", "mysql\+aiomysql"),
    ("mysql+mysqldb://u:p@localhost/cs", "mysql\+aiomysql"),
    ("dm+dmpython://SYSDBA:SYSDBA@localhost:5236/DAMENG", "dm\+dmAsync"),
    ("dm+dmPython://SYSDBA:SYSDBA@localhost:5236/DAMENG", "dm\+dmAsync"),
    ("sqlite:///./data/app.db", "sqlite\+aiosqlite"),
])
def test_sync_driver_is_rejected_with_async_alternative(url, keyword):
    with pytest.raises(DatabaseDriverError, match=keyword):
        ensure_driver(url)


@pytest.mark.parametrize("url", ["dm+dmasync://u:p@h:5236/d", "dm+DMPYTHON://u:p@h:5236/d"])
def test_dameng_driver_case_is_corrected(url):
    # 入口点大小写敏感：小写能过 URL 解析但加载不到方言，必须提前指出
    with pytest.raises(DatabaseDriverError, match=r"dm\+dmAsync"):
        ensure_driver(url)


# ── 厂商原厂方言：指给标准协议替代方案 ────────────────────

@pytest.mark.parametrize("url,keyword", [
    ("kingbase8://u:p@localhost:54321/db", "postgresql\+asyncpg"),
    ("opengauss://u:p@localhost:5432/db", "postgresql\+asyncpg"),
])
def test_vendor_dialect_points_to_standard_protocol(url, keyword):
    with pytest.raises(DatabaseDriverError, match=keyword):
        ensure_driver(url)


def test_unknown_scheme_lists_all_supported():
    with pytest.raises(DatabaseDriverError) as exc:
        ensure_driver("oracle+cx_oracle://u:p@localhost/orcl")
    msg = str(exc.value)
    assert "postgresql+asyncpg" in msg
    assert "dm+dmAsync" in msg


def test_malformed_url_is_translated():
    with pytest.raises(DatabaseDriverError, match="无法解析"):
        ensure_driver("not a url at all")


# ── 缺包：报错必须带出确切的 pip 命令 ────────────────────

def test_missing_driver_names_the_pip_package(monkeypatch):
    """asyncpg 已装的机器上也能验证：把 find_spec 打桩成找不到。"""
    real = importlib.util.find_spec

    def fake(name, *args, **kwargs):
        if name == "asyncpg":
            return None
        return real(name, *args, **kwargs)

    monkeypatch.setattr(importlib.util, "find_spec", fake)
    with pytest.raises(DatabaseDriverError, match=r"pip install asyncpg"):
        ensure_driver("postgresql+asyncpg://u:p@localhost/cs")


@pytest.mark.skipif(
    importlib.util.find_spec("dmAsync") is not None,
    reason="本机装了达梦驱动，缺包路径在 Linux 信创环境才走得到",
)
def test_dameng_missing_drivers_points_to_xinchuang_requirements():
    """macOS / 普通 Linux 开发机：达梦三件套都没装。"""
    with pytest.raises(DatabaseDriverError) as exc:
        ensure_driver("dm+dmAsync://SYSDBA:SYSDBA@localhost:5236/DAMENG")
    msg = str(exc.value)
    assert "requirements-xinchuang.txt" in msg
    # 缺的包要点名，不能只说「驱动缺失」
    assert "dmAsync" in msg


# ── 与建引擎集成：错误类型就是 DatabaseDriverError ─────────

def test_get_engine_raises_friendly_error(monkeypatch):
    from src.core import database

    class _DB:
        url = "dm+dmAsync://SYSDBA:SYSDBA@localhost:5236/DAMENG"
        echo = False

    monkeypatch.setattr(database, "get_settings", lambda: type("S", (), {"database": _DB()})())
    monkeypatch.setattr(database, "_engine", None)
    with pytest.raises(DatabaseDriverError):
        database.get_engine()
