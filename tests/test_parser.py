"""Tests for dsn_extractor.parser — Slice 1."""

from dsn_extractor.parser import parse_lines, parse, DSNRecord, ParsedDSN


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def assert_record_accounting(result: ParsedDSN) -> None:
    """Every record in all_records appears in exactly one bucket, no duplicates."""
    bucket_ids: set[int] = set()
    count = 0

    for r in result.file_level_records:
        bucket_ids.add(id(r))
        count += 1
    for est in result.establishments:
        for r in est.records:
            bucket_ids.add(id(r))
            count += 1
        for emp in est.employee_blocks:
            for r in emp.records:
                bucket_ids.add(id(r))
                count += 1
        for group in est.s54_blocks:
            for r in group:
                bucket_ids.add(id(r))
                count += 1
    for emp in result.unassigned_employee_blocks:
        for r in emp.records:
            bucket_ids.add(id(r))
            count += 1
    for group in result.unassigned_s54_blocks:
        for r in group:
            bucket_ids.add(id(r))
            count += 1

    # No duplicates (unique ids == total items counted)
    assert len(bucket_ids) == count, "Duplicate record detected across buckets"
    # No record lost
    assert count == len(result.all_records), (
        f"Record accounting mismatch: {count} in buckets vs {len(result.all_records)} total"
    )


def _non_blank_line_count(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip())


# ---------------------------------------------------------------------------
# TestParseLines — basic regex line parser
# ---------------------------------------------------------------------------

class TestParseLines:
    def test_basic_line(self):
        text = "S10.G00.00.001,'P24V01'"
        records, skipped = parse_lines(text)
        assert len(records) == 1
        assert records[0] == DSNRecord("S10.G00.00.001", "P24V01", 1)
        assert skipped == []

    def test_empty_value(self):
        text = "S21.G00.30.001,''"
        records, skipped = parse_lines(text)
        assert len(records) == 1
        assert records[0].raw_value == ""

    def test_blank_lines_skipped(self):
        text = "S10.G00.00.001,'V1'\n\n\nS10.G00.01.001,'123'\n"
        records, skipped = parse_lines(text)
        assert len(records) == 2
        assert skipped == []

    def test_non_matching_lines_captured(self):
        text = "S10.G00.00.001,'V1'\nGARBAGE LINE\nS10.G00.01.001,'123'"
        records, skipped = parse_lines(text)
        assert len(records) == 2
        assert len(skipped) == 1
        assert skipped[0] == (2, "GARBAGE LINE")

    def test_line_numbers_correct(self):
        text = "S10.G00.00.001,'A'\n\nS10.G00.01.001,'B'\nS10.G00.01.002,'C'"
        records, _ = parse_lines(text)
        assert [r.line_number for r in records] == [1, 3, 4]

    def test_value_with_spaces_and_accents(self):
        text = "S10.G00.01.003,'SOCIETE GENERALE'"
        records, skipped = parse_lines(text)
        assert len(records) == 1
        assert records[0].raw_value == "SOCIETE GENERALE"
        assert skipped == []

    def test_line_count_guarantee(self):
        text = "S10.G00.00.001,'A'\nBAD\n\nS10.G00.01.001,'B'\n"
        records, skipped = parse_lines(text)
        assert len(records) + len(skipped) == _non_blank_line_count(text)


# ---------------------------------------------------------------------------
# TestParseLinesInputVariants — BOM, CRLF, malformed
# ---------------------------------------------------------------------------

class TestParseLinesInputVariants:
    def test_bom_stripped(self):
        text = "\ufeffS10.G00.00.001,'P24V01'\nS10.G00.01.001,'123'"
        records, skipped = parse_lines(text)
        assert len(records) == 2
        assert records[0].code == "S10.G00.00.001"
        assert records[0].raw_value == "P24V01"
        assert skipped == []

    def test_crlf_line_endings(self):
        text_lf = "S10.G00.00.001,'A'\nS10.G00.01.001,'B'"
        text_crlf = "S10.G00.00.001,'A'\r\nS10.G00.01.001,'B'"
        records_lf, _ = parse_lines(text_lf)
        records_crlf, _ = parse_lines(text_crlf)
        assert len(records_lf) == len(records_crlf)
        for a, b in zip(records_lf, records_crlf):
            assert a.code == b.code
            assert a.raw_value == b.raw_value

    def test_missing_quotes_is_skipped(self):
        text = "S10.G00.00.001,P24V01"
        records, skipped = parse_lines(text)
        assert len(records) == 0
        assert len(skipped) == 1

    def test_partial_match_is_skipped(self):
        text = "S10.G00.00.001,'P24V01' extra"
        records, skipped = parse_lines(text)
        assert len(records) == 0
        assert len(skipped) == 1

    def test_plain_garbage_is_skipped(self):
        text = "this is not a DSN line"
        records, skipped = parse_lines(text)
        assert len(records) == 0
        assert len(skipped) == 1
        assert skipped[0] == (1, "this is not a DSN line")


# ---------------------------------------------------------------------------
# TestParseLineCount — fixture line counts
# ---------------------------------------------------------------------------

class TestParseLineCount:
    def test_single_establishment(self, single_establishment_text):
        records, skipped = parse_lines(single_establishment_text)
        assert len(records) + len(skipped) == _non_blank_line_count(single_establishment_text)
        assert len(skipped) == 0

    def test_multi_establishment(self, multi_establishment_text):
        records, skipped = parse_lines(multi_establishment_text)
        assert len(records) + len(skipped) == _non_blank_line_count(multi_establishment_text)
        assert len(skipped) == 0

    def test_no_s54_blocks(self, no_s54_blocks_text):
        records, skipped = parse_lines(no_s54_blocks_text)
        assert len(records) + len(skipped) == _non_blank_line_count(no_s54_blocks_text)
        assert len(skipped) == 0

    def test_unknown_enum_codes(self, unknown_enum_codes_text):
        records, skipped = parse_lines(unknown_enum_codes_text)
        assert len(records) + len(skipped) == _non_blank_line_count(unknown_enum_codes_text)
        assert len(skipped) == 0

    def test_missing_contract_fields(self, missing_contract_fields_text):
        records, skipped = parse_lines(missing_contract_fields_text)
        assert len(records) + len(skipped) == _non_blank_line_count(missing_contract_fields_text)
        assert len(skipped) == 0

    def test_with_s54_blocks(self, with_s54_blocks_text):
        records, skipped = parse_lines(with_s54_blocks_text)
        assert len(records) + len(skipped) == _non_blank_line_count(with_s54_blocks_text)
        assert len(skipped) == 0


# ---------------------------------------------------------------------------
# TestRecordAccounting — invariant across all fixtures
# ---------------------------------------------------------------------------

class TestRecordAccounting:
    def test_single_establishment(self, single_establishment_text):
        assert_record_accounting(parse(single_establishment_text))

    def test_multi_establishment(self, multi_establishment_text):
        assert_record_accounting(parse(multi_establishment_text))

    def test_no_s54_blocks(self, no_s54_blocks_text):
        assert_record_accounting(parse(no_s54_blocks_text))

    def test_unknown_enum_codes(self, unknown_enum_codes_text):
        assert_record_accounting(parse(unknown_enum_codes_text))

    def test_missing_contract_fields(self, missing_contract_fields_text):
        assert_record_accounting(parse(missing_contract_fields_text))

    def test_with_s54_blocks(self, with_s54_blocks_text):
        assert_record_accounting(parse(with_s54_blocks_text))

    def test_empty_file(self):
        assert_record_accounting(parse(""))

    def test_file_level_only(self):
        text = "S10.G00.00.001,'P24V01'\nS20.G00.05.001,'01'\nS90.G00.90.001,'0'\n"
        assert_record_accounting(parse(text))

    def test_unassigned_employee(self):
        text = (
            "S10.G00.00.001,'P24V01'\n"
            "S21.G00.30.001,'ORPHAN'\n"
            "S21.G00.40.001,'01012025'\n"
            "S21.G00.11.001,'00011'\n"
            "S21.G00.30.001,'NORMAL'\n"
            "S21.G00.40.001,'01062020'\n"
            "S90.G00.90.001,'2'\n"
        )
        assert_record_accounting(parse(text))


# ---------------------------------------------------------------------------
# TestSegmentSingleEstablishment
# ---------------------------------------------------------------------------

class TestSegmentSingleEstablishment:
    def test_one_establishment(self, single_establishment_text):
        result = parse(single_establishment_text)
        assert len(result.establishments) == 1

    def test_employee_count(self, single_establishment_text):
        result = parse(single_establishment_text)
        est = result.establishments[0]
        assert len(est.employee_blocks) == 3

    def test_file_level_records_extracted(self, single_establishment_text):
        result = parse(single_establishment_text)
        file_codes = {r.code for r in result.file_level_records}
        assert any(c.startswith("S10.") for c in file_codes)
        assert any(c.startswith("S20.") for c in file_codes)
        assert any(c.startswith("S90.") for c in file_codes)

    def test_no_unassigned_blocks(self, single_establishment_text):
        result = parse(single_establishment_text)
        assert len(result.unassigned_employee_blocks) == 0
        assert len(result.unassigned_s54_blocks) == 0

    def test_no_warnings(self, single_establishment_text):
        result = parse(single_establishment_text)
        assert len(result.warnings) == 0

    def test_establishment_has_identity(self, single_establishment_text):
        result = parse(single_establishment_text)
        est = result.establishments[0]
        codes = [r.code for r in est.records]
        assert "S21.G00.11.001" in codes

    def test_employee_blocks_contain_contract_and_remuneration(self, single_establishment_text):
        result = parse(single_establishment_text)
        for emp in result.establishments[0].employee_blocks:
            codes = [r.code for r in emp.records]
            assert "S21.G00.30.001" in codes
            assert any(c.startswith("S21.G00.40.") or c.startswith("S21.G00.50.") for c in codes)

    def test_s54_blocks_on_establishment(self, single_establishment_text):
        result = parse(single_establishment_text)
        est = result.establishments[0]
        assert len(est.s54_blocks) == 2  # type 17 and type 18

    def test_s54_not_in_employee_records(self, single_establishment_text):
        result = parse(single_establishment_text)
        for emp in result.establishments[0].employee_blocks:
            for r in emp.records:
                assert not r.code.startswith("S21.G00.54."), (
                    f"S54 record {r.code} found inside employee block"
                )


# ---------------------------------------------------------------------------
# TestSegmentMultiEstablishment
# ---------------------------------------------------------------------------

class TestSegmentMultiEstablishment:
    def test_two_establishments(self, multi_establishment_text):
        result = parse(multi_establishment_text)
        assert len(result.establishments) == 2

    def test_employees_assigned_correctly(self, multi_establishment_text):
        result = parse(multi_establishment_text)
        est1 = result.establishments[0]
        est2 = result.establishments[1]
        assert len(est1.employee_blocks) == 2  # DUPONT + MARTIN
        assert len(est2.employee_blocks) == 1  # BERNARD

    def test_establishment_identity_codes(self, multi_establishment_text):
        result = parse(multi_establishment_text)
        est1_nics = [
            r.raw_value for r in result.establishments[0].records
            if r.code == "S21.G00.11.001"
        ]
        assert est1_nics == ["00011"]
        est2_nics = [
            r.raw_value for r in result.establishments[1].records
            if r.code == "S21.G00.11.001"
        ]
        assert est2_nics == ["00022"]

    def test_no_unassigned_blocks(self, multi_establishment_text):
        result = parse(multi_establishment_text)
        assert len(result.unassigned_employee_blocks) == 0
        assert len(result.unassigned_s54_blocks) == 0

    def test_s54_per_establishment(self, multi_establishment_text):
        result = parse(multi_establishment_text)
        est1 = result.establishments[0]
        est2 = result.establishments[1]
        # est1 has type 17, est2 has type 17 + type 19
        assert len(est1.s54_blocks) == 1
        assert len(est2.s54_blocks) == 2


# ---------------------------------------------------------------------------
# TestS54Routing
# ---------------------------------------------------------------------------

class TestS54Routing:
    def test_s54_on_establishment_not_employee(self, with_s54_blocks_text):
        result = parse(with_s54_blocks_text)
        est = result.establishments[0]
        # 3 S54 groups: type 17, 18, 19
        assert len(est.s54_blocks) == 3
        # No S54 in any employee
        for emp in est.employee_blocks:
            for r in emp.records:
                assert not r.code.startswith("S21.G00.54.")

    def test_s54_group_contents(self, with_s54_blocks_text):
        result = parse(with_s54_blocks_text)
        est = result.establishments[0]
        # Each S54 group should have .001 (type) and .002 (amount)
        for group in est.s54_blocks:
            assert len(group) == 2
            assert group[0].code == "S21.G00.54.001"
            assert group[1].code == "S21.G00.54.002"

    def test_s54_before_establishment_is_unassigned(self):
        text = (
            "S10.G00.00.001,'P24V01'\n"
            "S21.G00.54.001,'17'\n"
            "S21.G00.54.002,'100.00'\n"
            "S21.G00.11.001,'00011'\n"
            "S90.G00.90.001,'0'\n"
        )
        result = parse(text)
        assert len(result.unassigned_s54_blocks) == 1
        assert len(result.warnings) > 0
        assert any("S54" in w and "not assigned" in w for w in result.warnings)
        assert_record_accounting(result)

    def test_s54_flush_on_establishment_boundary(self):
        text = (
            "S10.G00.00.001,'P24V01'\n"
            "S21.G00.06.001,'00011'\n"
            "S21.G00.11.001,'00011'\n"
            "S21.G00.30.001,'EMP1'\n"
            "S21.G00.40.001,'01012020'\n"
            "S21.G00.54.001,'17'\n"
            "S21.G00.54.002,'200.00'\n"
            "S21.G00.06.001,'00022'\n"  # new establishment flushes S54
            "S21.G00.11.001,'00022'\n"
            "S90.G00.90.001,'1'\n"
        )
        result = parse(text)
        assert len(result.establishments) == 2
        # S54 should be on first establishment
        assert len(result.establishments[0].s54_blocks) == 1
        assert len(result.establishments[1].s54_blocks) == 0
        assert_record_accounting(result)

    def test_s54_flush_on_file_level_record(self):
        text = (
            "S10.G00.00.001,'P24V01'\n"
            "S21.G00.06.001,'00011'\n"
            "S21.G00.11.001,'00011'\n"
            "S21.G00.54.001,'18'\n"
            "S21.G00.54.002,'150.00'\n"
            "S90.G00.90.001,'0'\n"  # file-level flushes S54
        )
        result = parse(text)
        assert len(result.establishments[0].s54_blocks) == 1
        assert_record_accounting(result)

    def test_s54_flush_on_eof(self):
        text = (
            "S21.G00.06.001,'00011'\n"
            "S21.G00.11.001,'00011'\n"
            "S21.G00.54.001,'19'\n"
            "S21.G00.54.002,'75.00'\n"
            # EOF — no trailing S90
        )
        result = parse(text)
        assert len(result.establishments[0].s54_blocks) == 1
        assert_record_accounting(result)


# ---------------------------------------------------------------------------
# TestUnassignedBlocks
# ---------------------------------------------------------------------------

class TestUnassignedBlocks:
    def test_employee_before_establishment(self):
        text = (
            "S10.G00.00.001,'P24V01'\n"
            "S20.G00.05.001,'01'\n"
            "S21.G00.30.001,'ORPHAN'\n"
            "S21.G00.30.002,'WORKER'\n"
            "S21.G00.40.001,'01012025'\n"
            "S21.G00.11.001,'00011'\n"
            "S21.G00.30.001,'NORMAL'\n"
            "S21.G00.30.002,'EMPLOYEE'\n"
            "S90.G00.90.001,'2'\n"
        )
        result = parse(text)
        assert len(result.unassigned_employee_blocks) == 1
        assert len(result.warnings) > 0
        assert any("not assigned" in w for w in result.warnings)
        assert_record_accounting(result)

    def test_employee_after_establishment_is_assigned(self):
        text = (
            "S10.G00.00.001,'P24V01'\n"
            "S21.G00.30.001,'ORPHAN'\n"
            "S21.G00.40.001,'01012025'\n"
            "S21.G00.11.001,'00011'\n"
            "S21.G00.30.001,'NORMAL'\n"
            "S21.G00.40.001,'01062020'\n"
            "S90.G00.90.001,'2'\n"
        )
        result = parse(text)
        assert len(result.unassigned_employee_blocks) == 1
        assert len(result.establishments) == 1
        assert len(result.establishments[0].employee_blocks) == 1
        assert_record_accounting(result)

    def test_s54_before_establishment_is_unassigned(self):
        text = (
            "S10.G00.00.001,'P24V01'\n"
            "S21.G00.54.001,'17'\n"
            "S21.G00.54.002,'50.00'\n"
            "S21.G00.06.001,'00011'\n"
            "S21.G00.11.001,'00011'\n"
            "S90.G00.90.001,'0'\n"
        )
        result = parse(text)
        assert len(result.unassigned_s54_blocks) == 1
        assert any("S54" in w for w in result.warnings)
        assert_record_accounting(result)


# ---------------------------------------------------------------------------
# TestEdgeCases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_file(self):
        result = parse("")
        assert len(result.all_records) == 0
        assert len(result.establishments) == 0
        assert len(result.warnings) == 0
        assert_record_accounting(result)

    def test_file_level_only(self):
        text = (
            "S10.G00.00.001,'P24V01'\n"
            "S20.G00.05.001,'01'\n"
            "S90.G00.90.001,'0'\n"
        )
        result = parse(text)
        assert len(result.file_level_records) == 3
        assert len(result.establishments) == 0
        assert_record_accounting(result)

    def test_establishment_without_employees(self):
        text = (
            "S10.G00.00.001,'P24V01'\n"
            "S21.G00.06.001,'00011'\n"
            "S21.G00.11.001,'00011'\n"
            "S21.G00.11.002,'6201Z'\n"
            "S90.G00.90.001,'0'\n"
        )
        result = parse(text)
        assert len(result.establishments) == 1
        assert len(result.establishments[0].employee_blocks) == 0
        assert_record_accounting(result)

    def test_missing_contract_fields_parses(self, missing_contract_fields_text):
        result = parse(missing_contract_fields_text)
        assert len(result.establishments) == 1
        assert len(result.establishments[0].employee_blocks) == 2
        assert_record_accounting(result)

    def test_file_ending_mid_employee_block(self):
        """No trailing S90 — last employee must still be flushed."""
        text = (
            "S21.G00.06.001,'00011'\n"
            "S21.G00.11.001,'00011'\n"
            "S21.G00.30.001,'LAST'\n"
            "S21.G00.40.001,'01012025'\n"
            "S21.G00.50.002,'2000.00'\n"
        )
        result = parse(text)
        assert len(result.establishments) == 1
        assert len(result.establishments[0].employee_blocks) == 1
        assert_record_accounting(result)

    def test_file_ending_mid_s54_group(self):
        """S54 group at EOF with no trailing record — must be flushed."""
        text = (
            "S21.G00.06.001,'00011'\n"
            "S21.G00.11.001,'00011'\n"
            "S21.G00.54.001,'17'\n"
            "S21.G00.54.002,'100.00'\n"
        )
        result = parse(text)
        assert len(result.establishments[0].s54_blocks) == 1
        assert_record_accounting(result)

    def test_establishment_with_only_s06_no_s11(self):
        """Establishment declared via S21.G00.06 without S21.G00.11."""
        text = (
            "S10.G00.00.001,'P24V01'\n"
            "S21.G00.06.001,'00011'\n"
            "S21.G00.06.002,'11'\n"
            "S21.G00.30.001,'EMP1'\n"
            "S21.G00.40.001,'01012020'\n"
            "S90.G00.90.001,'1'\n"
        )
        result = parse(text)
        assert len(result.establishments) == 1
        assert len(result.establishments[0].employee_blocks) == 1
        # No S21.G00.11.001 in establishment records
        assert not any(
            r.code == "S21.G00.11.001" for r in result.establishments[0].records
        )
        assert_record_accounting(result)
