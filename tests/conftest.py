import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def single_establishment_path() -> Path:
    return FIXTURES_DIR / "single_establishment.dsn"


@pytest.fixture
def multi_establishment_path() -> Path:
    return FIXTURES_DIR / "multi_establishment.dsn"


@pytest.fixture
def no_s54_blocks_path() -> Path:
    return FIXTURES_DIR / "no_s54_blocks.dsn"


@pytest.fixture
def unknown_enum_codes_path() -> Path:
    return FIXTURES_DIR / "unknown_enum_codes.dsn"


@pytest.fixture
def missing_contract_fields_path() -> Path:
    return FIXTURES_DIR / "missing_contract_fields.dsn"


@pytest.fixture
def with_s54_blocks_path() -> Path:
    return FIXTURES_DIR / "with_s54_blocks.dsn"


@pytest.fixture
def single_establishment_text(single_establishment_path: Path) -> str:
    return single_establishment_path.read_text(encoding="utf-8")


@pytest.fixture
def multi_establishment_text(multi_establishment_path: Path) -> str:
    return multi_establishment_path.read_text(encoding="utf-8")


@pytest.fixture
def no_s54_blocks_text(no_s54_blocks_path: Path) -> str:
    return no_s54_blocks_path.read_text(encoding="utf-8")


@pytest.fixture
def unknown_enum_codes_text(unknown_enum_codes_path: Path) -> str:
    return unknown_enum_codes_path.read_text(encoding="utf-8")


@pytest.fixture
def missing_contract_fields_text(missing_contract_fields_path: Path) -> str:
    return missing_contract_fields_path.read_text(encoding="utf-8")


@pytest.fixture
def with_s54_blocks_text(with_s54_blocks_path: Path) -> str:
    return with_s54_blocks_path.read_text(encoding="utf-8")


@pytest.fixture
def with_absences_path() -> Path:
    return FIXTURES_DIR / "with_absences.dsn"


@pytest.fixture
def with_absences_text(with_absences_path: Path) -> str:
    return with_absences_path.read_text(encoding="utf-8")


@pytest.fixture
def with_unknown_exit_and_absence_codes_path() -> Path:
    return FIXTURES_DIR / "with_unknown_exit_and_absence_codes.dsn"


@pytest.fixture
def with_unknown_exit_and_absence_codes_text(
    with_unknown_exit_and_absence_codes_path: Path,
) -> str:
    return with_unknown_exit_and_absence_codes_path.read_text(encoding="utf-8")
