# Tasks: 001-payout-status

- [x] T001 Write contract `contracts/payout-state.schema.json` (nine fields)
- [x] T002 Write fixtures in `tests/fixtures/`: one per state, plus negative + in transit, pending + in transit, all zero
- [x] T003 Write failing tests in `tests/test_service.py`: one per state, the overlaps, contract shape, no hard-coded values
- [x] T004 `payout_state/templates.py`: parse owner messages and no_payout reasons from `docs/payout-states.md`
- [x] T005 `payout_state/service.py`: data selection, check order, column map, message fill
- [x] T006 `payout_state/__main__.py`: run on Maria's file and print the nine-field result
- [x] T007 Run tests and Maria's file as of 2026-11-16; record the result in `README.md`
