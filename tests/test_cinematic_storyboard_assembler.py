"""Unit tests for CinematicStoryboardAssembler."""

import pytest
from pathlib import Path
from backend.core.cinematic_storyboard_assembler import (
    CinematicStoryboardAssembler,
    StoryboardScene,
    StoryboardShot,
)


@pytest.fixture
def assembler():
    return CinematicStoryboardAssembler()


SAMPLE_FOUNTAIN = """
EXT. CYBERPUNK METROPOLIS - NIGHT

Rain lashes against holographic billboards towering over neon canyons. Neon light reflects on wet asphalt.

ELENA
(whispering)
They know we're here. We have to move now.

MARCUS
Not before I get the core decrypted.

He slams his cybernetic palm onto the terminal interface. Sparks burst from the circuit housing.
"""


def test_parse_fountain(assembler):
    scenes = assembler.parse_fountain(SAMPLE_FOUNTAIN)
    assert len(scenes) >= 1
    sc = scenes[0]
    assert sc.setting == "EXT"
    assert "CYBERPUNK" in sc.location.upper()
    assert sc.time_of_day == "NIGHT"

    # Verify shots were generated
    assert len(sc.shots) >= 3
    # Check action shot
    assert any("Wide" in sh.shot_scale for sh in sc.shots)
    # Check dialogue shot
    dialogue_shots = [sh for sh in sc.shots if sh.dialogue is not None]
    assert len(dialogue_shots) >= 2
    assert dialogue_shots[0].dialogue.character == "ELENA"
    assert "They know" in dialogue_shots[0].dialogue.text
    assert dialogue_shots[0].dialogue.parenthetical == "whispering"


def test_build_assembly_manifest(assembler, tmp_path):
    scenes = assembler.parse_fountain(SAMPLE_FOUNTAIN)
    manifest = assembler.build_assembly_manifest(
        project_name="Cyberpunk_Infiltration",
        scenes=scenes,
        bgm_path="ambient_synth.wav",
        resolution="1920x1080",
        fps=24,
    )

    assert manifest["project_name"] == "Cyberpunk_Infiltration"
    assert manifest["total_shots"] == len(manifest["scenes"])
    assert manifest["estimated_runtime_sec"] > 0
    assert manifest["bgm_audio_path"] == "ambient_synth.wav"

    out_json = tmp_path / "test_manifest.json"
    assembler.export_manifest_json(manifest, out_json)
    assert out_json.exists()
    assert "Cyberpunk_Infiltration" in out_json.read_text(encoding="utf-8")
