"""把「缺少数据库驱动」翻译成可直接照做的安装指引。

没有这层时，写错连接串或少装一个驱动，SQLAlchemy 抛的是::

    sqlalchemy.exc.NoSuchModuleError: Can't load plugin:
    sqlalchemy.dialects:dm.dmAsync

信创现场的人看到这句话通常不知道该装哪个包。这里按连接串的
``方言+驱动`` 提前探测，缺了就报出确切的 pip 命令。

本项目的引擎是纯异步的（``create_async_engine``），所以只接受异步
DBAPI；误填 psycopg2 / pymysql / dmPython 这类同步驱动时，同样在这里
拦住并指出对应的异步写法。
"""
from __future__ import annotations

import importlib.util
from dataclasses import dataclass

from sqlalchemy.engine import make_url, URL


class DatabaseDriverError(RuntimeError):
    """DATABASE_URL 用到的驱动没装、是同步驱动，或方言根本不支持。"""


@dataclass(frozen=True)
class _Spec:
    # 建引擎前必须能 find_spec 到的模块（一个方言可能由多个包组成）。
    modules: tuple[str, ...]
    # 缺包时给出的安装指引。
    install: str
    # 补充说明（平台限制、认证注意事项等）。
    note: str = ""


# key = (方言 backend, 驱动 driver)，即连接串 scheme 里 ``+`` 两边。
_ASYNC_SPECS: dict[tuple[str, str], _Spec] = {
    ("sqlite", "aiosqlite"): _Spec(
        ("aiosqlite",), "pip install aiosqlite（requirements.txt 已包含）"),
    ("mysql", "aiomysql"): _Spec(
        ("aiomysql",), "pip install aiomysql（requirements.txt 已包含）",
        "TiDB、OceanBase（MySQL 租户）、GaussDB(for MySQL) 走同一协议，直接可用。"),
    ("postgresql", "asyncpg"): _Spec(
        ("asyncpg",), "pip install asyncpg（requirements.txt 已包含）",
        "PostgreSQL 及走 PG 协议的信创库通用：人大金仓 KingbaseES（PG 兼容模式，"
        "默认端口 54321）、openGauss、瀚高 HighGo、海量 Vastbase G100、"
        "华为 GaussDB（PG 兼容版）。注意 openGauss 默认 sha256 认证 asyncpg "
        "不支持，需在服务端改成 md5/scram 认证。"),
    ("postgresql", "psycopg"): _Spec(
        ("psycopg",), "pip install 'psycopg[binary]'",
        "psycopg 3 自带异步支持，同样可连接走 PG 协议的信创库。"),
    ("dm", "dmAsync"): _Spec(
        # dmAsync 是异步兼容层，dmSQLAlchemy 注册 dm+dmAsync 方言，dmPython
        # 是底层 DBAPI —— 三个包少一个都连不上，所以一起探。
        ("dmAsync", "dmSQLAlchemy", "dmPython"),
        "pip install -r requirements-xinchuang.txt",
        "达梦 DM8 原厂驱动只有 Linux（x86_64/aarch64，适配麒麟、统信）和 "
        "Windows 的编译 wheel，没有 macOS 版。默认端口 5236。"),
}

# 常见的「驱动装上了，但是同步版」错误 —— 装包解决不了，得改连接串。
_SYNC_DRIVER_HINTS: dict[tuple[str, str], str] = {
    ("postgresql", "psycopg2"):
        "psycopg2 是同步驱动，而本项目使用异步引擎。请把连接串改为 "
        "postgresql+asyncpg://（pip install asyncpg），或改用 psycopg 3："
        "postgresql+psycopg://（pip install 'psycopg[binary]'）。",
    ("mysql", "pymysql"):
        "pymysql 是同步驱动。请把连接串改为 mysql+aiomysql://"
        "（pip install aiomysql，requirements.txt 已包含）。",
    ("mysql", "mysqldb"):
        "MySQLdb 是同步驱动。请把连接串改为 mysql+aiomysql://。",
    ("dm", "dmpython"):
        "dmPython 是同步驱动。请把连接串改为 dm+dmAsync://（注意大小写），并执行 "
        "pip install -r requirements-xinchuang.txt（仅 Linux/Windows）。",
    ("dm", "dmPython"):
        "dmPython 是同步驱动。请把连接串改为 dm+dmAsync://，并执行 "
        "pip install -r requirements-xinchuang.txt（仅 Linux/Windows）。",
    ("sqlite", "pysqlite"):
        "内置 sqlite3 是同步驱动。请把连接串改为 sqlite+aiosqlite://"
        "（pip install aiosqlite）。",
}

# 信创原厂方言名（装了厂商客户端才会出现）。项目不直接支持，给出走标准协议的替代写法。
_VENDOR_DIALECT_HINTS: dict[str, str] = {
    "kingbase8":
        "人大金仓 KingbaseES 请在初始化数据库时选择 PG 兼容模式，连接串用 "
        "postgresql+asyncpg://（默认端口 54321，驱动 asyncpg 已在 requirements.txt）。"
        "原厂 kingbase8 方言是同步的，无法用于本项目的异步引擎。",
    "opengauss":
        "openGauss 请改用 postgresql+asyncpg:// 连接，并在服务端使用 md5/scram "
        "认证（默认 sha256 认证只有 openGauss 自家的同步 psycopg2 分支支持）。",
}

# 裸 scheme（不写 ``+driver``）时各方言的默认 DBAPI —— 全是同步驱动，
# 所以补上名字后会落进 _SYNC_DRIVER_HINTS，提示用户改成异步写法。
_DEFAULT_DRIVERS = {
    "sqlite": "pysqlite",
    "mysql": "mysqldb",
    "postgresql": "psycopg2",
    "dm": "dmpython",
}

_SUPPORTED_SCHEMES = (
    "sqlite+aiosqlite://",
    "mysql+aiomysql://",
    "postgresql+asyncpg://",
    "postgresql+psycopg://",
    "dm+dmAsync://",
)


def parse_url(url: str) -> URL:
    """解析连接串，格式错误也翻成中文。"""
    try:
        return make_url(url)
    except Exception as e:  # sqlalchemy.exc.ArgumentError 等
        raise DatabaseDriverError(
            f"DATABASE_URL 格式无法解析：{url!r}\n"
            "形如 dialect+driver://用户:密码@主机:端口/库名，"
            f"本项目支持的 scheme：{', '.join(_SUPPORTED_SCHEMES)}"
        ) from e


def ensure_driver(url: str) -> URL:
    """按连接串探测驱动；缺失/不支持时抛 ``DatabaseDriverError``。

    返回解析后的 URL，供调用方直接拿去建引擎，避免再解析一次。
    """
    parsed = parse_url(url)
    # 不调 parsed.get_driver_name()：裸 scheme（如 ``dm://``）会让 SQLAlchemy
    # 现加载方言入口点来查默认驱动名，方言包没装时这一步自己就抛
    # NoSuchModuleError，我们反而没机会说人话。
    if "+" in parsed.drivername:
        backend, driver = parsed.drivername.split("+", 1)
    else:
        backend, driver = parsed.drivername, ""

    # 连方言都没装的厂商原厂 scheme（kingbase8:// 等），先给标准协议替代方案。
    if backend in _VENDOR_DIALECT_HINTS:
        raise DatabaseDriverError(
            f"DATABASE_URL 使用了厂商原厂方言 {backend}://，本项目不直接支持。\n"
            + _VENDOR_DIALECT_HINTS[backend]
        )

    if not driver:
        # SQLAlchemy 为裸 scheme 选的默认 DBAPI 全是同步驱动（pysqlite /
        # mysqldb / psycopg2 / dmpython），补成默认名后交给下面的同步驱动表提示。
        driver = _DEFAULT_DRIVERS.get(backend, "")

    # 达梦方言入口点对大小写敏感（dm.dmAsync / dm.dmPython），小写能解析 URL
    # 但加载不到入口点，提前把正确写法指出来。
    if backend == "dm" and driver.lower() in {"dmasync", "dmpython"} \
            and driver not in {"dmAsync", "dmPython"}:
        raise DatabaseDriverError(
            f"DATABASE_URL 里的达梦驱动名大小写不对：dm+{driver}。"
            "异步请写 dm+dmAsync，同步方言名为 dm+dmPython（本项目需要前者）。"
        )

    key = (backend, driver)

    if key in _SYNC_DRIVER_HINTS:
        raise DatabaseDriverError(
            f"DATABASE_URL 使用了同步驱动 {backend}+{driver}。\n"
            + _SYNC_DRIVER_HINTS[key]
        )

    spec = _ASYNC_SPECS.get(key)
    if spec is None:
        shown = f"{backend}+{driver}" if driver else f"{backend}://"
        raise DatabaseDriverError(
            f"不认识的数据库连接方式：{shown}（DATABASE_URL={url}）。\n"
            f"本项目支持：{', '.join(_SUPPORTED_SCHEMES)}。\n"
            "信创数据库一般兼容 PostgreSQL 或 MySQL 协议，换成对应标准 scheme "
            "通常即可连接；达梦 DM8 请见 requirements-xinchuang.txt。"
        )

    missing = [m for m in spec.modules if importlib.util.find_spec(m) is None]
    if missing:
        raise DatabaseDriverError(
            f"缺少数据库驱动：DATABASE_URL={url} 需要 {', '.join(missing)}。\n"
            f"请在 backend/ 目录执行：{spec.install}\n"
            + (f"注意：{spec.note}" if spec.note else "")
        )

    return parsed


def wrap_engine_error(url: str, exc: Exception) -> DatabaseDriverError:
    """建引擎瞬间仍可能抛 NoSuchModuleError（方言包在、入口点没注册等），统一兜底。"""
    return DatabaseDriverError(
        f"数据库方言加载失败（DATABASE_URL={url}）：{exc}\n"
        "请对照 README「关系型数据库（含信创）」一节检查驱动安装；"
        "达梦需安装 requirements-xinchuang.txt 里的 dmPython / dmSQLAlchemy / dmAsync 三个包。"
    )


__all__ = [
    "DatabaseDriverError",
    "ensure_driver",
    "parse_url",
    "wrap_engine_error",
]
