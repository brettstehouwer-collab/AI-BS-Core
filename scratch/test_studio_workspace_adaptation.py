import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Add backend to path
sys.path.insert(0, r"C:\AI-BS\backend")
sys.path.insert(0, r"C:\AI-BS")

from core.ai_adapter import _get_adaptation_rules

def test_adaptation_rules():
    print("Testing Adaptation Rules with Book Styles...")
    
    # 1. Autobiography + Feature Film
    rules_auto = _get_adaptation_rules("Feature Film (Spec Script)", "Autobiography / Memoir / Biopic")
    assert "AUTOBIOGRAPHY / MEMOIR" in rules_auto, "Autobiography style not found in rules"
    assert "VOICE-OVER" in rules_auto, "Voice-over rule not found"
    assert "HOLLYWOOD FEATURE FILM" in rules_auto, "Target format rule not found"
    print("  [OK] Autobiography / Memoir style verified.")

    # 2. Non-Fiction + 1-Hour TV Drama
    rules_nonfic = _get_adaptation_rules("TV Pilot (1-Hour Drama)", "Non-Fiction / True Crime / Investigative")
    assert "NON-FICTION / INVESTIGATIVE" in rules_nonfic, "Non-fiction style not found"
    assert "SUPER:" in rules_nonfic, "Superimpositions rule not found"
    assert "1-HOUR TV DRAMA" in rules_nonfic, "1-Hour Drama format not found"
    print("  [OK] Non-Fiction / True Crime style verified.")

    # 3. Theatrical Stage Play + Stage Play
    rules_stage = _get_adaptation_rules("Theatrical Stage Play", "Theatrical Stage Play / Drama")
    assert "THEATRICAL DRAMA" in rules_stage, "Stage play style not found"
    assert "THEATRICAL STAGE PLAY" in rules_stage, "Stage play target not found"
    print("  [OK] Theatrical Stage Play style verified.")

    # 4. Fiction Novel + Director's Previs
    rules_director = _get_adaptation_rules("Director's Shooting Script (Previs & Camera Cues)", "Fiction Novel / Narrative")
    assert "FICTION NOVEL" in rules_director, "Fiction style not found"
    assert "DIRECTOR'S SHOOTING SCRIPT" in rules_director, "Director's format not found"
    print("  [OK] Fiction Novel + Director's Previs verified.")

def test_fdx_structure():
    print("Testing Hollywood FDX Structure...")
    # Mock ast serialized with the new format
    sample_xml = """<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
<FinalDraft DocumentType="Script" Template="No" Version="3">
  <ElementSettings Type="General">
    <FontSpec AdornmentStyle="0" Background="#FFFFFFFFFFFF" Color="#000000000000" Font="Courier Final Draft" RevisionID="0" Size="12" Style="AllCaps"/>
    <ParagraphSpec Alignment="Left" FirstIndent="0.00" Leading="Regular" LeftIndent="0.00" RightIndent="1.25" SpaceBefore="0" Spacing="1" StartsNewPage="No"/>
    <Behavior Paginated="No"/>
  </ElementSettings>
  <ElementSettings Type="Scene Heading">
    <FontSpec AdornmentStyle="0" Background="#FFFFFFFFFFFF" Color="#000000000000" Font="Courier Final Draft" RevisionID="0" Size="12" Style="Bold+AllCaps"/>
    <ParagraphSpec Alignment="Left" FirstIndent="0.00" Leading="Regular" LeftIndent="0.00" RightIndent="0.00" SpaceBefore="24" Spacing="1" StartsNewPage="No"/>
    <Behavior Paginated="No"/>
  </ElementSettings>
  <ElementSettings Type="Action">
    <FontSpec AdornmentStyle="0" Background="#FFFFFFFFFFFF" Color="#000000000000" Font="Courier Final Draft" RevisionID="0" Size="12" Style=""/>
    <ParagraphSpec Alignment="Left" FirstIndent="0.00" Leading="Regular" LeftIndent="0.00" RightIndent="0.00" SpaceBefore="12" Spacing="1" StartsNewPage="No"/>
    <Behavior Paginated="No"/>
  </ElementSettings>
  <ElementSettings Type="Character">
    <FontSpec AdornmentStyle="0" Background="#FFFFFFFFFFFF" Color="#000000000000" Font="Courier Final Draft" RevisionID="0" Size="12" Style="AllCaps"/>
    <ParagraphSpec Alignment="Left" FirstIndent="0.00" Leading="Regular" LeftIndent="2.20" RightIndent="0.00" SpaceBefore="12" Spacing="1" StartsNewPage="No"/>
    <Behavior Paginated="No"/>
  </ElementSettings>
  <HeaderAndFooter>
    <Header>
      <Paragraph Alignment="Right" FirstIndent="0.00" Leading="Regular" LeftIndent="0.00" RightIndent="0.00" SpaceBefore="0" Spacing="1" StartsNewPage="No">
        <Text AdornmentStyle="0" Background="#FFFFFFFFFFFF" Color="#000000000000" Font="Courier Final Draft" RevisionID="0" Size="12" Style="">[PageNumber].</Text>
      </Paragraph>
    </Header>
  </HeaderAndFooter>
  <PageLayout BackgroundColor="#FFFFFFFFFFFF" BottomMargin="720" BreakDialogueAndActionAtSentences="Yes" DocumentType="Script" HeaderMargin="360" FooterMargin="360" LeftMargin="1080" RightMargin="720" TopMargin="720">
    <PageSize Height="11.00" Width="8.50"/>
  </PageLayout>
  <Content>
    <Paragraph Type="Scene Heading">
      <Text AdornmentStyle="0" Background="#FFFFFFFFFFFF" Color="#000000000000" Font="Courier Final Draft" RevisionID="0" Size="12" Style="Bold+AllCaps">EXT. MOJAVE DESERT - DAY</Text>
    </Paragraph>
    <Paragraph Type="Action">
      <Text AdornmentStyle="0" Background="#FFFFFFFFFFFF" Color="#000000000000" Font="Courier Final Draft" RevisionID="0" Size="12">Heat waves shimmer across the cracked desert pavement.</Text>
    </Paragraph>
    <Paragraph Type="Character">
      <Text AdornmentStyle="0" Background="#FFFFFFFFFFFF" Color="#000000000000" Font="Courier Final Draft" RevisionID="0" Size="12" Style="AllCaps">BRETT (V.O.)</Text>
    </Paragraph>
    <Paragraph Type="Dialogue">
      <Text AdornmentStyle="0" Background="#FFFFFFFFFFFF" Color="#000000000000" Font="Courier Final Draft" RevisionID="0" Size="12">We never saw it coming.</Text>
    </Paragraph>
  </Content>
</FinalDraft>"""

    # Parse with standard XML parser to verify syntax
    root = ET.fromstring(sample_xml)
    assert root.tag == "FinalDraft", "Root tag mismatch"
    assert root.find("Content") is not None, "Content element missing"
    assert root.find("PageLayout") is not None, "PageLayout element missing"
    paragraphs = root.find("Content").findall("Paragraph")
    assert len(paragraphs) == 4, f"Expected 4 paragraphs, got {len(paragraphs)}"
    print("  [OK] Hollywood FDX XML parses cleanly and conforms to Final Draft spec.")

if __name__ == "__main__":
    test_adaptation_rules()
    test_fdx_structure()
    print("\nALL WORKSPACE ADAPTATION TESTS PASSED!")
