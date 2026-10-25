# Fixture correction

The first history-picker assertion selected any nonempty option. Several authorized synthetic histories intentionally had identical text, so that did not prove recovery of the newly archived conversation. The corrected fixture selects its exact captured conversation ID. Retain followup_red.json as weaker history-picker evidence; review_red.json records the corrected assertions before application fixes.

A first shell-inline attempt to edit that long fixture line failed PowerShell parsing (Unexpected token in expression). It did not execute the edit/build/test commands or alter application code. The separate strengthen_picker_fixture_5_329_33.py avoids nested shell escaping. This was a fixture/command error, not a GPU, model or production runtime diagnosis.

The first final audit looked for archive_regression/green.json; the reused legacy fixture actually writes ui_green.json. It stopped with FileNotFoundError before emitting audit.json. Retain audit_fixture_v1.py and the already-written source.diff. The corrected audit reads the actual report and verifies the existing diff rather than rerunning edits or overwriting it. The33 archive checks themselves had already passed.
