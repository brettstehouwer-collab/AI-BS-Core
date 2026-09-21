import re
import json
from pathlib import Path

# Expanded archetypes, vocal descriptors and voice tag patterns
ARCHETYPE_RULES = [
    # Female Roles & Keywords
    {
        "keywords": ["ELLA", "MOM", "MOTHER", "WIFE", "MARIA", "CARMELA", "DONNA"],
        "gender": "Female",
        "role": "Matriarch / Emotional Anchor",
        "voice_tag": "[Warm, emotional Female Voice]",
        "vocal_tone": "Warm, resonant, protective, emotional depth",
        "default_style": "Caring, protective, emotionally grounded, steadfast"
    },
    {
        "keywords": ["WILLOW", "STELLA", "SINGER", "VOCALIST", "PERFORMER", "HOST"],
        "gender": "Female",
        "role": "Charismatic Performer / Manager",
        "voice_tag": "[Playful, charismatic Female Singer Voice]",
        "vocal_tone": "Melodic, dynamic, vibrant, captivating stage presence",
        "default_style": "Lively, witty, hospitable, quick with conversational banter"
    },
    {
        "keywords": ["ARIANA", "DANCER", "BALLERINA", "GIRL", "INGENUE"],
        "gender": "Female",
        "role": "Lead Ballerina / Sensitive Protagonist",
        "voice_tag": "[Soft, emotive Ballerina Voice]",
        "vocal_tone": "Gentle, lyrical, vulnerable, poised",
        "default_style": "Graceful, cautious, perceptive, expressive delivery"
    },
    {
        "keywords": ["JULIANNA", "OFFICER", "DETECTIVE", "COP", "AGENT", "INSPECTOR"],
        "gender": "Female",
        "role": "Undercover Law Enforcement / Investigator",
        "voice_tag": "[Focused, measured Undercover Cop Voice]",
        "vocal_tone": "Crisp, analytical, sharp, disciplined cadence",
        "default_style": "Perceptive, cautious, tactical, investigative questions"
    },
    {
        "keywords": ["LADY SOPHIA", "SOPHIA", "QUEEN", "MADAM", "DUCHESS", "ARISTOCRAT"],
        "gender": "Female",
        "role": "Aristocratic Power Player / Enigmatic Assassin",
        "voice_tag": "[Sophisticated, icy Aristocratic Female Voice]",
        "vocal_tone": "Velvety, chillingly composed, aristocratic, deliberate pauses",
        "default_style": "Cultured, cold, razor-sharp, untouchable elegance"
    },
    {
        "keywords": ["CHANEL", "DAUGHTER", "CHILD", "LITTLE", "GIRL", "KID"],
        "gender": "Female",
        "role": "Innocent Youth / Patient Fighter",
        "voice_tag": "[Tender, quiet Child Female Voice]",
        "vocal_tone": "Sweet, quiet, delicate, youthful innocence",
        "default_style": "Gentle, honest, heartfelt, soft-spoken"
    },
    {
        "keywords": ["DR. XAVIER", "XAVIER", "DOCTOR", "PHYSICIAN", "CORONER", "PATHOLOGIST"],
        "gender": "Female",
        "role": "Forensic Pathologist / Scientific Mind",
        "voice_tag": "[Cool, scientific Female Pathologist Voice]",
        "vocal_tone": "Objective, clinical, cool, intellectually acute",
        "default_style": "Direct medical observations, precise terminology, unshakeable demeanor"
    },
    {
        "keywords": ["JULIE", "GUEST", "ARTIST", "MUSICIAN"],
        "gender": "Female",
        "role": "Featured Guest Artist / Vocalist",
        "voice_tag": "[Bright, melodic Featured Singer Voice]",
        "vocal_tone": "Bright, uplifting, expressive, resonant soprano/alto",
        "default_style": "Warm, inspiring, artistically refined"
    },
    {
        "keywords": ["NURSE", "CAREGIVER", "SISTER"],
        "gender": "Female",
        "role": "Medical Caregiver / Guardian",
        "voice_tag": "[Calm, clinical Female Voice]",
        "vocal_tone": "Reassuring, measured, gentle authority",
        "default_style": "Professional, empathetic, calm under emergency pressure"
    },
    {
        "keywords": ["GIRLFRIEND", "WAITRESS", "MAID", "WOMAN", "LADY"],
        "gender": "Female",
        "role": "Secondary Female Figure / Witness",
        "voice_tag": "[Expressive, natural Female Voice]",
        "vocal_tone": "Spontaneous, realistic conversational register",
        "default_style": "Casual, reactive, situational"
    },

    # Male Roles & Keywords
    {
        "keywords": ["JACK", "DON", "BOSS", "GODFATHER", "CAPO", "CHIEF"],
        "gender": "Male",
        "role": "Syndicate Boss / Kingpin",
        "voice_tag": "[Deep, commanding Mob Boss Male Voice]",
        "vocal_tone": "Deep, authoritative, gravelly baritone, gravelled weight",
        "default_style": "Calculated, dominant, ruthless, quiet menace"
    },
    {
        "keywords": ["NATHAN", "DETECTIVE", "COP", "INVESTIGATOR", "MARSHAL", "SHERIFF"],
        "gender": "Male",
        "role": "Conflicted Lawman / Protective Father",
        "voice_tag": "[Gritty, morally conflicted Detective Male Voice]",
        "vocal_tone": "Weary, gritty, grounded tenor/baritone, heavy moral friction",
        "default_style": "Tired realism, cynical wit, desperate protective instinct"
    },
    {
        "keywords": ["VICTOR", "CONSIGLIERE", "ENFORCER", "RIGHT HAND", "SOLDIER"],
        "gender": "Male",
        "role": "Consigliere / Seasoned Enforcer",
        "voice_tag": "[Composed, steady Enforcer Male Voice]",
        "vocal_tone": "Low, steady, unwavering, quiet lethal confidence",
        "default_style": "Loyal, brief, observant, unflinching obedience to code"
    },
    {
        "keywords": ["JOEY", "WISEGUY", "TRIGGERMAN", "HOOD", "PUNKER"],
        "gender": "Male",
        "role": "Streetwise Enforcer / Triggerman",
        "voice_tag": "[Brash, fast-talking Wiseguy Male Voice]",
        "vocal_tone": "High-energy, brash, rhythmic Brooklyn/Detroit slang",
        "default_style": "Hot-tempered, confrontational, rapid-fire humor and threats"
    },
    {
        "keywords": ["BOBBY", "CAPTAIN", "LIEUTENANT", "ENFORCER"],
        "gender": "Male",
        "role": "Territorial Mob Captain",
        "voice_tag": "[Gruff, aggressive Mob Captain Male Voice]",
        "vocal_tone": "Gravelly, raspy, heavy, booming chest resonance",
        "default_style": "Short-fused, territorial, blunt, commanding"
    },
    {
        "keywords": ["MATT", "ASSOCIATE", "SMUGGLER", "GAMBLER"],
        "gender": "Male",
        "role": "Crew Associate / Sarcastic Confidant",
        "voice_tag": "[Sarcastic, humorous Associate Male Voice]",
        "vocal_tone": "Chuckle in the voice, wry, sarcastic, animated",
        "default_style": "Dry sarcasm, comedic relief, relaxed under pressure"
    },
    {
        "keywords": ["GIOVANNI", "MARCO", "RIVAL", "TRAITOR", "THIEF"],
        "gender": "Male",
        "role": "Rival Family Infiltrator / Antagonist",
        "voice_tag": "[Defiant, raspy Rival Mobster Male Voice]",
        "vocal_tone": "Tense, raspy, defiant, cornered aggression",
        "default_style": "Stubborn, sharp, refusing to break until cornered"
    },
    {
        "keywords": ["MALCOLM", "BOUNCER", "BODYGUARD", "SECURITY", "BOXER", "FIGHTER"],
        "gender": "Male",
        "role": "Head of Security / Martial Artist",
        "voice_tag": "[Deep, disciplined Bodyguard Male Voice]",
        "vocal_tone": "Bass-baritone, calm, immovably solid, polite threat",
        "default_style": "Courteous, minimal words, total physical authority"
    },
    {
        "keywords": ["BRETT", "BARTENDER", "HOST", "PUB"],
        "gender": "Male",
        "role": "Pub Owner / Upbeat Host",
        "voice_tag": "[Youthful, upbeat Bartender Male Voice]",
        "vocal_tone": "Warm, social, upbeat, energetic tenor",
        "default_style": "Welcoming, humorous, quick with drinks and banter"
    },
    {
        "keywords": ["ERIN", "COMIC", "COMEDIAN", "MC"],
        "gender": "Male",
        "role": "Stand-up Comedian / MC",
        "voice_tag": "[Animated, comedic Standup Performer Male Voice]",
        "vocal_tone": "Punchy, expressive, crowd-pleasing, comedic timing",
        "default_style": "Improvised punchlines, self-deprecating, audience banter"
    },
    {
        "keywords": ["SEAN", "BARBACK", "RUNNER"],
        "gender": "Male",
        "role": "Barback / Stylish Wingman",
        "voice_tag": "[Smooth, casual Barback Male Voice]",
        "vocal_tone": "Smooth, relaxed, high-scale swagger",
        "default_style": "Effortless confidence, supportive humor"
    },
    {
        "keywords": ["BISHOP", "FATHER", "PRIEST", "CLERGY", "PASTOR", "ALLEN", "THOMAS"],
        "gender": "Male",
        "role": "Diocesan Bishop / Spiritual Confessor",
        "voice_tag": "[Resonant, dignified Clergy Male Voice]",
        "vocal_tone": "Solemn, rich baritone, gentle pacing, moral weight",
        "default_style": "Compassionate scrutiny, theological depth, perceptive listener"
    },
    {
        "keywords": ["HUDSON", "LIEUTENANT", "CAPTAIN", "CHIEF"],
        "gender": "Male",
        "role": "Senior Police Official",
        "voice_tag": "[Authoritative Police Lieutenant Male Voice]",
        "vocal_tone": "Gruff, stern, bureaucratic, commanding",
        "default_style": "Demanding deadlines, blunt orders, hidden motives"
    },
    {
        "keywords": ["ADAM", "ELIJAH", "SON", "BOY", "TEEN", "BROTHER"],
        "gender": "Male",
        "role": "Adolescent Son / Protective Brother",
        "voice_tag": "[Earnest Adolescent Male Voice]",
        "vocal_tone": "Young tenor, questioning, earnest, slightly guarded",
        "default_style": "Direct questions, loyalty to family, youthful vulnerability"
    },
    {
        "keywords": ["HENCHMAN", "GUNMAN", "SHOOTER", "THUG", "HITMAN"],
        "gender": "Male",
        "role": "Contract Hitman / Shooter",
        "voice_tag": "[Sinister, low Hitman Male Voice]",
        "vocal_tone": "Low, menacing, gravelly, predatory whisper",
        "default_style": "Cold statements, threatening precision"
    }
]

def derive_personality_from_dialogue(clean_name: str, dialogues: list) -> str:
    """
    Analyzes actual character spoken lines to deduce psychological traits,
    emotional temperaments, priorities, and conversational patterns.
    """
    if not dialogues:
        return "Adaptable and situational conversationalist responding directly to immediate scene pressures."
        
    combined = " ".join(dialogues).lower()
    traits = []
    
    # 1. Aggression / Hostility vs Kindness / Affection
    curse_count = len(re.findall(r'\b(fuck|fucking|shit|ass|bitch|damn|hell)\b', combined))
    affection_count = len(re.findall(r'\b(babe|love|sweetheart|son|honey|daughter|daddy|mom)\b', combined))
    authority_count = len(re.findall(r'\b(need|want|order|tell|listen|make sure|understand|let me)\b', combined))
    question_count = combined.count('?')
    
    if curse_count >= 2:
        traits.append("confrontational, aggressive, emotionally volatile, uses forceful profanity to assert dominance")
    elif affection_count >= 2:
        traits.append("deeply affectionate, family-centric, values emotional attachments and protective bonds")
        
    if authority_count >= 4:
        traits.append("commanding, hierarchical, habituated to directing others, expects compliance")
    elif question_count >= 4:
        traits.append("inquisitive, cautious, seeks validation, navigating high ambiguity or suspicion")
        
    # 2. Vocabulary & Tone markers
    if any(k in combined for k in ["god", "church", "mass", "father", "bishop", "sin", "bless", "faith"]):
        traits.append("spiritually conscious, navigating moral guilt or using religious cover")
    if any(k in combined for k in ["money", "paid", "dollars", "cash", "triple", "bill", "bills"]):
        traits.append("transactional, financially driven, acutely aware of material costs and leverage")
    if any(k in combined for k in ["secret", "secrets", "loyalty", "trust", "code", "turf", "family"]):
        traits.append("deeply bound to syndicate codes of omertà, obsessed with loyalty, paranoid of betrayal")
    if any(k in combined for k in ["dance", "sing", "ballet", "show", "music", "cheers", "stage", "routine"]):
        traits.append("artistically devoted, expressive, thrives in performance and social celebration")
    if any(k in combined for k in ["doctor", "hospital", "nurse", "dead", "body", "bullet", "pathology", "vascular"]):
        traits.append("hardened by crisis and mortality, clinically observational or gripped by medical trauma")
        
    if not traits:
        traits.append("measured, direct, pragmatically focused on immediate objectives")
        
    avg_len = sum(len(d.split()) for d in dialogues) / max(1, len(dialogues))
    if avg_len > 25:
        cadence = "Delivers articulate, expansive monologues showing deep internal processing."
    elif avg_len < 8:
        cadence = "Sparse, clipped, guarded speech; rarely wastes words."
    else:
        cadence = "Balanced, natural conversational rhythm adapted to scene dynamics."
        
    return f"{'; '.join(traits).capitalize()}. {cadence}"


def extract_dialogues_by_character(corpus: str) -> dict:
    """Extracts list of all spoken dialogue lines per character across the corpus."""
    char_dialogues = {}
    lines = corpus.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        clean = re.sub(r'\s*\(.*?\)\s*', '', line).strip().upper()
        if clean.isupper() and 2 <= len(clean) <= 25 and not any(clean.startswith(x) for x in [
            'INT', 'EXT', 'EST', 'FADE', 'CUT', 'TITLE', 'AUTHOR', 'CREDIT', 'DRAFT', 'PAGE', 'BBC', 'CONTINUED'
        ]):
            if i + 1 < len(lines):
                nxt = lines[i+1].strip()
                if nxt and not nxt.isupper() and not nxt.startswith('INT') and not nxt.startswith('EXT'):
                    speech = []
                    j = i + 1
                    while j < len(lines) and lines[j].strip() and not lines[j].strip().isupper():
                        if not re.match(r'^\d+\.?$', lines[j].strip()) and not re.match(r'^\(?CONTINUED.*?\)??$', lines[j].strip(), re.I):
                            speech.append(lines[j].strip())
                        j += 1
                    if speech:
                        char_dialogues.setdefault(clean, []).append(' '.join(speech))
                    i = j
                    continue
        i += 1
    return char_dialogues


def analyze_character(cand_name: str, corpus: str, char_dialogues: dict = None) -> dict:
    """
    Builds an exhaustive, studio-grade character dossier matching Suno v6 table read specs,
    including vocal pitch, gender, acoustics, physical lore, and dialogue-deduced personality.
    """
    clean_name = cand_name.strip().upper()
    dialogue_list = (char_dialogues or {}).get(clean_name, [])
    
    # 1. Match archetype rule
    matched_rule = None
    for rule in ARCHETYPE_RULES:
        if any(k == clean_name or k in clean_name.split() for k in rule["keywords"]):
            matched_rule = rule
            break
            
    if not matched_rule:
        # Fallback gender heuristic
        female_signals = ["MRS", "MS", "MISS", "GIRL", "WOMAN", "LADY", "SISTER", "AUNT", "MOTHER"]
        if any(s in clean_name for s in female_signals):
            gender = "Female"
            role = "Supporting Female Character"
            voice_tag = f"[{clean_name.title()} (Expressive Female Voice)]"
            vocal_pitch = "Medium Mezzo-Soprano (Natural, expressive register)"
            vocal_tone = "Clear, natural, responsive feminine register"
            accent = "Natural conversational delivery"
            personality_base = "Responsive, intuitive, protective"
            default_style = "Natural conversational dialogue"
        else:
            gender = "Male"
            role = "Supporting Male Character"
            voice_tag = f"[{clean_name.title()} (Grounded Male Voice)]"
            vocal_pitch = "Medium Baritone (Grounded, natural resonance)"
            vocal_tone = "Grounded, natural masculine resonance"
            accent = "Natural conversational delivery"
            personality_base = "Pragmatic, direct, situationally reactive"
            default_style = "Natural conversational dialogue"
    else:
        gender = matched_rule["gender"]
        role = matched_rule["role"]
        voice_tag = matched_rule["voice_tag"]
        vocal_pitch = matched_rule.get("vocal_pitch", "Medium-High Soprano" if gender == "Female" else "Low-Medium Baritone")
        vocal_tone = matched_rule["vocal_tone"]
        accent = matched_rule.get("accent", "Standard American")
        personality_base = matched_rule.get("personality", "Dramatic narrative figure")
        default_style = matched_rule["default_style"]

    # 2. Dialogue-based personality analysis
    dialogue_personality = derive_personality_from_dialogue(clean_name, dialogue_list)
    full_personality = f"{personality_base}. [Dialogue Insights]: {dialogue_personality}"

    # 3. Extract specific physical description from text
    intro_pattern = re.compile(
        rf'{re.escape(clean_name)}[,\s]+([0-9]{{1,2}}(?:\'s|s)?(?:,\s*|\s+)[^\.\n]{{5,250}}?)(?:\.|\n|$)',
        re.IGNORECASE
    )
    intro_match = intro_pattern.search(corpus)
    
    physical_lore = ""
    if intro_match:
        physical_lore = intro_match.group(1).strip()
    else:
        sent_match = re.search(rf'([^\.\n]*?{re.escape(clean_name)}[^\.\n]*?\.)', corpus, re.IGNORECASE)
        if sent_match:
            physical_lore = sent_match.group(1).strip()

    # Formulate rich biography
    bio_parts = [
        f"**Role & Archetype:** {role}",
        f"**Gender / Voice Profile:** {gender} — {voice_tag}",
        f"**Vocal Pitch & Acoustics:** {vocal_pitch} | {vocal_tone}",
        f"**Accent & Cadence:** {accent}",
        f"**Personality Profile (Drawn from Spoken Dialogue):**\n{full_personality}"
    ]
    if physical_lore:
        bio_parts.append(f"**Physical Traits & Background:**\n{physical_lore}")
    else:
        bio_parts.append(f"**Physical Traits & Background:**\nActive dramatic figure interacting across scenes in the narrative.")
        
    if dialogue_list:
        sample_quotes = ' "' + '" / "'.join([d[:80] for d in dialogue_list[:3]]) + '"'
        bio_parts.append(f"**Key Spoken Dialogue Samples ({len(dialogue_list)} lines):**\n{sample_quotes}")
        
    full_bio = "\n\n".join(bio_parts)

    return {
        "name": clean_name,
        "gender": gender,
        "role": role,
        "voice_tag": voice_tag,
        "vocal_pitch": vocal_pitch,
        "vocal_tone": vocal_tone,
        "accent": accent,
        "personality": full_personality,
        "bio": full_bio,
        "speaking_style": default_style
    }

def extract_project_characters(fountain_text: str, source_text: str = "") -> list:
    """
    Intelligently extracts all characters from a screenplay or source book,
    populating detailed descriptions, bios, pitches, genders, and dialogue-deduced personalities.
    """
    characters = []
    seen = set()
    corpus = (fountain_text or "") + "\n" + (source_text or "")
    char_dialogues = extract_dialogues_by_character(corpus)

    # Extract Character speaking cues
    char_cue_pattern = re.compile(r'^\s*([A-Z][A-Z0-9\s\.\'\-]{1,25})(?:\s*\(.*?\))?\s*$', re.MULTILINE)
    
    for match in char_cue_pattern.finditer(fountain_text or ""):
        cand = match.group(1).strip()
        cand_clean = re.sub(r'\s*\(.*?\)\s*', '', cand).strip()
        
        # Exclude non-character cues
        if cand_clean in [
            "INT", "EXT", "INT/EXT", "EST", "FADE IN", "FADE OUT", "FADE TO BLACK",
            "CUT TO", "SMASH CUT", "DISSOLVE TO", "THE END", "CONTINUED", "TITLE",
            "CREDIT", "AUTHOR", "SOURCE", "DRAFT DATE", "BBC SCREENPLAY FORMAT"
        ]:
            continue
            
        if len(cand_clean) >= 2 and cand_clean not in seen:
            seen.add(cand_clean)
            char_dossier = analyze_character(cand_clean, corpus, char_dialogues)
            characters.append(char_dossier)

    return characters
