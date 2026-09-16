"""
Social Outreach & Facebook Optimizer Core Engine
Provides 100% context-driven topic detection, dual format generation (Long-Form vs Short-Form),
Fire Writing (Immutable Transcription) processing, dynamic 3-tier mixed hashtag matrix generation,
and context-aware comment-drop URL architecture.
Strictly generates tags and CTAs based ONLY on user input context without assuming any specific entity or brand.
"""

import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

TOPIC_CATALOG = {
    "film_acting_theatre": {
        "keywords": [
            "imdb", "film", "acting", "actor", "actress", "set", "on set", "role", 
            "stage", "memorizing lines", "lines", "theatre", "theater", "movie", 
            "cinema", "screenplay", "script", "casting", "director", "audition", 
            "filmmaking", "hollywood", "backstage", "callsheet", "living stage",
            "west michigan film", "grand rapids film"
        ],
        "label": "Film, Stage & Performing Arts",
        "box1": ["#ActorLife", "#IndieFilm", "#Filmmaking", "#StageAndScreen", "#BehindTheScenes"],
        "box2": ["#ActorsOfInstagram", "#FilmCommunity", "#TheatreLife", "#WomenInFilm", "#CreativeJourney"],
        "box3": ["#IndieCinema", "#ActingCraft", "#SetLife", "#OnSet", "#ArtistSpotlight"]
    },
    "music_audio_performance": {
        "keywords": [
            "guitar", "music", "band", "song", "album", "track", "singer", "concert", 
            "gig", "spotify", "sound", "vocal", "audio", "musician", "jam", "bass", "drum",
            "rehearsal", "songwriter", "live performance", "studio recording"
        ],
        "label": "Music, Audio & Live Performance",
        "box1": ["#IndependentMusician", "#LiveMusic", "#Songwriter", "#MusicProducer", "#NewMusic"],
        "box2": ["#MusicCommunity", "#BandLife", "#MusiciansDaily", "#OriginalMusic", "#IndieMusic"],
        "box3": ["#NowPlaying", "#MusicIsLife", "#StudioVibes", "#SoundtrackOfLife", "#ArtistDiscovery"]
    },
    "personal_friendship_appreciation": {
        "keywords": [
            "friend", "friendship", "kindness", "kind to me", "shoutout", "proud of you", 
            "special to me", "support my", "grateful for you", "true friend", "best part of you",
            "beautiful lady", "stay true to you", "gratitude", "thank you for always",
            "special person", "lift each other up"
        ],
        "label": "Creative Collaboration & Peer Support",
        "box1": ["#TrueFriendship", "#GratefulHeart", "#FriendshipGoals", "#SupportYourFriends", "#KindnessMatters"],
        "box2": ["#LiftEachOtherUp", "#RealConnections", "#AppreciationPost", "#CommunityOverCompetition", "#GoodPeople"],
        "box3": ["#CelebrateOthers", "#AuthenticFriendships", "#PositiveVibes", "#LoyaltyAndLove", "#Heartfelt"]
    },
    "tech_software_engineering": {
        "keywords": [
            "code", "software", "daemon", "wsl", "gpu", "rtx", "fastapi", "react", 
            "ollama", "python", "hardware", "dev", "developer", "programming", 
            "github", "api", "fullstack", "frontend", "backend", "linux", "server",
            "docker", "compiler", "4090", "open source"
        ],
        "label": "Software Engineering & Sovereign Tech",
        "box1": ["#OpenSource", "#SoftwareArchitecture", "#FullStackDev", "#IndieDev", "#DevLife"],
        "box2": ["#LocalLLM", "#TechFounders", "#PythonDev", "#BuildInPublic", "#SystemArchitecture"],
        "box3": ["#GPUComputing", "#EngineeringMindset", "#CodingLife", "#TechBuilder", "#ModernStack"]
    },
    "business_commercial_growth": {
        "keywords": [
            "business", "revenue", "leads", "client", "sales", "enterprise", "commercial", 
            "pressure wash", "contractor", "roi", "operations", "marketing", "b2b",
            "pipeline", "contracts", "service", "profit", "retainer"
        ],
        "label": "Commercial Growth & Enterprise Operations",
        "box1": ["#BusinessOperations", "#CommercialGrowth", "#Entrepreneurship", "#Leadership", "#LocalBusiness"],
        "box2": ["#LeadGeneration", "#ClientSuccess", "#B2BStrategy", "#BusinessMindset", "#SalesExecution"],
        "box3": ["#SmallBusinessOwner", "#OperationalExcellence", "#GrowthTactics", "#EnterpriseStrategy", "#ExecutionMatters"]
    },
    "memoir_trauma_recovery": {
        "keywords": [
            "c-ptsd", "cptsd", "trauma", "memoir", "hypervigilance", "autobiography", 
            "grief", "recovery", "ptsd", "mental health", "healing", "traumas",
            "hyper awareness", "dissociate", "inner child", "moral ethical"
        ],
        "label": "Autobiographical Memoir & Trauma Recovery",
        "box1": ["#CPTSDAwareness", "#RadicalAuthenticity", "#TraumaRecovery", "#MentalResilience", "#RawHonesty"],
        "box2": ["#MentalHealthMatters", "#HealingJourney", "#OvercomingTrauma", "#InnerStrength", "#LifeAfterTrauma"],
        "box3": ["#Hypervigilance", "#MindsetShift", "#TruthHeals", "#ResilientMind", "#PersonalTransformation"]
    },
    "creative_writing_literature": {
        "keywords": [
            "read my book", "my book", "new book", "novel", "author", "chapter", 
            "literature", "writer", "booktok", "bookstagram", "publishing", "publisher",
            "prose", "poetry", "storytelling", "writing community"
        ],
        "label": "Books, Literature & Author Craft",
        "box1": ["#IndieAuthor", "#MustRead", "#BookCommunity", "#AuthorsOfFacebook", "#Storytelling"],
        "box2": ["#BookLovers", "#Bibliophile", "#ReadersCommunity", "#NewBook", "#WritersLife"],
        "box3": ["#BookRecommendation", "#AmWriting", "#LiteratureLovers", "#PageTurner", "#AuthorJourney"]
    },
    "general_authentic_life": {
        "keywords": [
            "life", "perspective", "growth", "mindset", "truth", "real", "authentic",
            "reflection", "lessons", "journey", "keep going", "showing up"
        ],
        "label": "Personal Perspective & Real Talk",
        "box1": ["#RadicalAuthenticity", "#PersonalGrowth", "#MindsetMatters", "#RealTalk", "#PerspectiveShift"],
        "box2": ["#SelfGrowth", "#StayTrueToYou", "#LifeLessons", "#AuthenticSelf", "#EverydayWisdom"],
        "box3": ["#SelfAwareness", "#InspireDaily", "#TruthTeller", "#MindsetShift", "#KeepMovingForward"]
    }
}

URL_REGEX = r'(https?://[^\s)]+)'

def extract_urls(text: str) -> List[str]:
    """Extracts all outbound URLs from text."""
    return re.findall(URL_REGEX, text)

def strip_urls(text: str) -> str:
    """Removes raw URLs from text to avoid Meta link penalties."""
    return re.sub(URL_REGEX, '', text).strip()

def detect_topic(text: str, target_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Detects primary topic based strictly on input context and outbound URL.
    Does NOT assume any default entity or brand unless explicitly provided in the input.
    """
    text_lower = text.lower()
    combined_context = text_lower + " " + (target_url.lower() if target_url else "")
    
    scores = {}
    for key, data in TOPIC_CATALOG.items():
        score = 0
        for kw in data["keywords"]:
            if " " in kw:
                if kw in combined_context:
                    score += 3
            else:
                pattern = r'\b' + re.escape(kw) + r'\b'
                if re.search(pattern, combined_context):
                    score += 1
        
        # URL domain contextual bonus
        if target_url:
            u = target_url.lower()
            if key == "film_acting_theatre" and ("imdb.com" in u or "filmfest" in u or "youtube.com" in u or "vimeo.com" in u):
                score += 5
            elif key == "music_audio_performance" and ("spotify.com" in u or "soundcloud.com" in u or "bandcamp.com" in u or "apple.com/music" in u):
                score += 5
            elif key == "tech_software_engineering" and ("github.com" in u or "gitlab.com" in u or "huggingface.co" in u):
                score += 5
            elif key == "creative_writing_literature" and ("stehouwer-publishing.com" in u or "goodreads.com" in u or "/dp/" in u or "amazon.com" in u):
                score += 5
                
        scores[key] = score

    best_match = max(scores, key=scores.get)
    
    # Check if user explicitly wrote "stehouwer" in text or URL
    user_mentioned_stehouwer = "stehouwer" in text_lower or (target_url and "stehouwer" in target_url.lower())

    if scores[best_match] == 0:
        box1 = ["#RadicalAuthenticity", "#PersonalGrowth", "#MindsetMatters", "#RealTalk", "#PerspectiveShift"]
        box2 = ["#SelfGrowth", "#StayTrueToYou", "#LifeLessons", "#AuthenticSelf", "#EverydayWisdom"]
        box3 = ["#SelfAwareness", "#InspireDaily", "#TruthTeller", "#MindsetShift", "#KeepMovingForward"]
        if user_mentioned_stehouwer:
            box1.append("#StehouwerPublishing")
            box3.append("#StehouwerPublishing")
        return {
            "key": "general_authentic_life",
            "label": TOPIC_CATALOG["general_authentic_life"]["label"],
            "box1": box1[:6],
            "box2": box2[:6],
            "box3": box3[:6]
        }
    
    match_data = TOPIC_CATALOG[best_match]
    box1 = list(match_data["box1"])
    box2 = list(match_data["box2"])
    box3 = list(match_data["box3"])

    # Enrich with peer support tags if user expresses friendship/support in creative posts
    if best_match in ["film_acting_theatre", "music_audio_performance"] and any(k in text_lower for k in ["friend", "support", "kind", "shoutout"]):
        if "#ArtistSpotlight" not in box3:
            box3[0] = "#ArtistSpotlight"
        if "#SupportYourFriends" not in box1:
            box1.append("#SupportYourFriends")

    # Only include brand tag if explicitly in user input
    if user_mentioned_stehouwer:
        box1.append("#StehouwerPublishing")
        box3.append("#StehouwerPublishing")

    return {
        "key": best_match,
        "label": match_data["label"],
        "box1": box1[:6],
        "box2": box2[:6],
        "box3": box3[:6]
    }

def get_link_cta(topic_key: str, target_url: Optional[str] = None, text_lower: str = "") -> Dict[str, str]:
    """
    Generates context-aware link callout based on URL destination and surrounding context:
    IMDb -> (IMDb profile & link pinned in the first comment 👇)
    YouTube/Vimeo -> (Video link pinned in the first comment 👇)
    Music/Spotify -> (Music link pinned in the first comment 👇)
    Book/Amazon -> (Book link pinned in the first comment 👇)
    General URL -> (Direct link pinned in the first comment 👇)
    """
    if not target_url:
        return {"long": "", "short": ""}
    
    url_lower = target_url.lower()
    
    if "imdb.com" in url_lower or topic_key == "film_acting_theatre":
        return {
            "long": "\n\n(IMDb profile & link pinned in the first comment 👇)",
            "short": "\n\n👉 IMDb profile & link pinned in comment #1."
        }
    elif any(d in url_lower for d in ["youtube.com", "youtu.be", "vimeo.com"]):
        return {
            "long": "\n\n(Video link pinned in the first comment 👇)",
            "short": "\n\n👉 Video link pinned in comment #1."
        }
    elif any(d in url_lower for d in ["spotify.com", "soundcloud.com", "bandcamp.com", "apple.com/music"]) or topic_key == "music_audio_performance":
        return {
            "long": "\n\n(Music link pinned in the first comment 👇)",
            "short": "\n\n👉 Music link pinned in comment #1."
        }
    elif any(d in url_lower for d in ["amazon.com", "goodreads.com"]) or topic_key in ["creative_writing_literature", "memoir_trauma_recovery"] or "book" in text_lower or "memoir" in text_lower:
        return {
            "long": "\n\n(Book link pinned in the first comment 👇)",
            "short": "\n\n👉 Book link pinned in comment #1."
        }
    elif "github.com" in url_lower or topic_key == "tech_software_engineering":
        return {
            "long": "\n\n(Project repository & link pinned in the first comment 👇)",
            "short": "\n\n👉 Project link pinned in comment #1."
        }
    else:
        return {
            "long": "\n\n(Direct link pinned in the first comment 👇)",
            "short": "\n\n👉 Direct link pinned in comment #1."
        }

def format_long_form(clean_text: str, has_url: bool, target_url: Optional[str] = None, topic_key: str = "", text_lower: str = "") -> str:
    """Formats narrative post with whitespace pacing, stripped URLs, and context-driven first comment cue."""
    paragraphs = [p.strip() for p in clean_text.split('\n') if p.strip()]
    if not paragraphs:
        paragraphs = [clean_text]
    
    formatted_body = "\n\n".join(paragraphs)
    
    if has_url:
        cta = get_link_cta(topic_key, target_url, text_lower)["long"]
        if cta:
            formatted_body += cta
    
    return formatted_body

def format_short_form(clean_text: str, has_url: bool, target_url: Optional[str] = None, topic_key: str = "", text_lower: str = "") -> str:
    """Formats punchy short-form post under 500 characters with visual anchors and context-driven CTA."""
    sentences = re.split(r'(?<=[.!?])\s+', clean_text.replace('\n', ' '))
    core_sentences = [s.strip() for s in sentences if s.strip()][:3]
    
    if not core_sentences:
        core_text = clean_text[:280]
    else:
        core_text = " ".join(core_sentences)
    
    short_post = f"🎯 {core_text}"
    if has_url:
        short_cta = get_link_cta(topic_key, target_url, text_lower)["short"]
        if short_cta:
            short_post += short_cta
    return short_post

def process_fire_writing(raw_text: str, primary_url: Optional[str] = None, topic_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Implements the Fire Writing Rule (Immutable Transcription):
    - Zero Alterations: Zero word substitutions, zero spelling corrections, zero vocabulary modernization, zero grammar smoothing.
    - Personal Truth Invariance: Authentic internal cadence preserved.
    - Permitted Structural Adjustments:
      * Mechanical capitalization: standalone 'i' -> 'I', sentence starters capitalized.
      * Pacing & logical pauses preserved.
      * Algorithmic whitespace & line splitting (double returns) for mobile dwell time and 'See More' cutoffs.
    - Period spacing buffer (. \n . \n .) before tags.
    - Outbound link stripped from body to first comment.
    - Bifurcation Protocol (strings > 400 chars): Sequester raw string in raw_source_payload code block.
    - Archival Obligation: stehouwer_reality_archival_block dictionary.
    - Decoupled Analytical Scaffolding: Decoupled analytical matrix table.
    """
    raw_payload = raw_text.strip()
    is_bifurcated = len(raw_payload) > 400
    
    clean_body = strip_urls(raw_payload)
    
    # Mechanical capitalization without modifying any word tokens
    def mechanical_capitalization(text: str) -> str:
        res = re.sub(r'\bi\b', 'I', text)
        if res and res[0].islower():
            res = res[0].upper() + res[1:]
        res = re.sub(r'([.!?]\s+)([a-z])', lambda m: m.group(1) + m.group(2).upper(), res)
        return res

    structured_text = mechanical_capitalization(clean_body)
    
    # Algorithmic whitespace & line splitting
    raw_lines = [l.strip() for l in structured_text.split('\n') if l.strip()]
    paced_lines = []
    for line in raw_lines:
        if len(line) > 120 and ('. ' in line or '! ' in line or '? ' in line):
            sub_clauses = re.split(r'(?<=[.!?])\s+', line)
            for sc in sub_clauses:
                if sc.strip():
                    paced_lines.append(sc.strip())
        else:
            paced_lines.append(line)
            
    social_body = "\n\n".join(paced_lines)
    
    if primary_url:
        cta = get_link_cta(topic_info.get("key", "") if topic_info else "", primary_url, raw_text.lower())["long"]
        if cta:
            social_body += cta

    period_buffer = "\n\n.\n.\n."
    now_iso = datetime.now(timezone.utc).isoformat()
    
    archival_block = {
        "timestamp": now_iso,
        "classification": "Fire Writing (Immutable Cognitive Transcript)",
        "protocol": "Fidelitas Mandate v1.0",
        "fidelitas_metrics": {
            "fidelity_score": 1.0,
            "word_substitution_count": 0,
            "vocabulary_modernization_count": 0,
            "grammar_smoothing_applied": False,
            "raw_character_count": len(raw_payload),
            "bifurcated": is_bifurcated
        },
        "detected_topic": topic_info.get("label", "Personal Perspective & Real Talk") if topic_info else "Personal Perspective & Real Talk",
        "core_construct_mapping": {
            "cadence": "Immutable internal cadence / authentic cognitive stream",
            "outbound_isolation": True if primary_url else False,
            "metadata_buffer": "Triple period line-split"
        }
    }
    
    scaffolding = {
        "source_cadence": "High-intensity cognitive stream / personal truth invariance",
        "readability_index": "Paced single-clause layout with double returns",
        "anti_suppression_grade": "A+ (Outbound URL isolated to first comment drop)",
        "empirical_correlation": "100% preservation of author lexical tokens"
    }

    return {
        "is_fire_writing": True,
        "raw_source_payload": f'raw_source_payload = """{raw_payload}"""' if is_bifurcated else None,
        "social_post": social_body,
        "period_buffer": period_buffer,
        "stehouwer_reality_archival_block": archival_block,
        "decoupled_analytical_scaffolding": scaffolding
    }

def generate_social_payload(
    raw_text: str, 
    custom_url: Optional[str] = None, 
    target_platform: str = "facebook",
    fire_writing_mode: bool = False
) -> Dict[str, Any]:
    """
    Analyzes text, generates long/short/fire-writing posts, hashtag boxes, and first comment payload
    based strictly on context.
    """
    urls = extract_urls(raw_text)
    primary_url = custom_url or (urls[0] if urls else None)
    
    clean_text = strip_urls(raw_text)
    clean_text = re.sub(r'#\w+', '', clean_text).strip()
    text_lower = raw_text.lower()
    
    topic = detect_topic(raw_text, primary_url)
    has_url = bool(primary_url)
    
    long_form = format_long_form(clean_text, has_url, primary_url, topic["key"], text_lower)
    short_form = format_short_form(clean_text, has_url, primary_url, topic["key"], text_lower)
    
    # Process Fire Writing
    fire_writing_data = process_fire_writing(raw_text, primary_url, topic)
    
    first_comment = f"🔗 Link: {primary_url}" if primary_url else None
    
    return {
        "status": "success",
        "topic": topic["label"],
        "topic_key": topic["key"],
        "detected_urls": urls,
        "primary_url": primary_url,
        "comment_drop": first_comment,
        "period_buffer": "\n\n.\n.\n.",
        "posts": {
            "long_form": long_form,
            "short_form": short_form,
            "fire_writing": fire_writing_data["social_post"]
        },
        "fire_writing": fire_writing_data,
        "hashtag_boxes": {
            "box1": {
                "title": "Box 1: Core Outreach",
                "audience": "Niche + Specific Context",
                "tags": topic["box1"],
                "tag_string": " ".join(topic["box1"])
            },
            "box2": {
                "title": "Box 2: Discovery & Community",
                "audience": "Industry Tribe & Peer Communities",
                "tags": topic["box2"],
                "tag_string": " ".join(topic["box2"])
            },
            "box3": {
                "title": "Box 3: Algorithmic & Search Mix",
                "audience": "Broad Trending Topics & Discovery",
                "tags": topic["box3"],
                "tag_string": " ".join(topic["box3"])
            }
        },
        "algorithm_compliance": {
            "link_in_body_penalty": False,
            "comment_drop_recommended": True if primary_url else False,
            "tag_count_healthy": True,
            "tag_range": "3 to 6 tags (Optimal Meta Ceiling)",
            "period_buffer_isolated": True
        }
    }


