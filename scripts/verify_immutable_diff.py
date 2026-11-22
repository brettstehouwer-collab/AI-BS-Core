"""
Deterministic Verification Script for Role 49 (immutable_fire_scribe)
Verifies 100% lexical word-order fidelity while permitting non-word formatting.
"""

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.core.subagent_coordinator import verify_immutable_transcription


def main() -> int:
    raw_sample = "we need to build the custom engine renderer right now and deploy to firebase"
    valid_formatted = (
        "- **We** need to build the *Custom Engine* renderer right now,\n"
        "- and deploy to Firebase!"
    )
    invalid_paraphrased = (
        "- We should compile the custom engine renderer immediately and push to Firebase."
    )

    ok_check = verify_immutable_transcription(raw_sample, valid_formatted)
    if not ok_check.get("verified_verbatim") or ok_check.get("word_accuracy") != 1.0:
        print(f"[FAIL] Valid formatted text failed verification: {ok_check}", file=sys.stderr)
        return 1

    bad_check = verify_immutable_transcription(raw_sample, invalid_paraphrased)
    if bad_check.get("verified_verbatim"):
        print(f"[FAIL] Paraphrased text erroneously passed verification: {bad_check}", file=sys.stderr)
        return 1

    print(
        f"IMMUTABLE_DIFF_VERIFIED: word_count={ok_check['raw_word_count']} "
        f"accuracy={ok_check['word_accuracy']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
