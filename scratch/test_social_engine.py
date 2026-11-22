"""
Test scratch script to verify context-driven social optimizer engine.
"""
import re
from typing import Dict, Any, List, Optional

TOPIC_CATALOG = {
    "film_stage_arts": {
        "keywords": [
            "imdb", "film", "acting", "actor", "actress", "set", "on set", "role", 
            "stage", "memorizing lines", "lines", "theatre", "theater", "movie", 
            "cinema", "screenplay", "script", "casting", "director", "audition", 
            "filmmaking", "hollywood", "backstage", "callsheet", "living stage"
        ],
        "label": "Film, Stage & Performing Arts",
        "box1": ["#ActorLife", "#IndieFilm", "#Filmmaking", "#StageAndScreen", "#BehindTheScenes"],
        "box2": ["#ActorsOfInstagram", "#FilmCommunity", "#TheatreLife", "#WomenInFilm", "#CreativeJourney"],
        "box3": ["#IndieCinema", "#ActingCraft", "#SetLife", "#OnSet", "#ArtistSpotlight"]
    },
    "music_audio_performance": {
        "keywords": [
            "guitar", "music", "band", "song", "album", "track", "singer", "concert", 
            "gig", "spotify", "sound", "vocal", "audio", "musician", "jam", "bass", "drum"
        ],
        "label": "Music, Audio & Live Performance",
        "box1": ["#IndependentMusician", "#LiveMusic", "#Songwriter", "#MusicProducer", "#NewMusic"],
        "box2": ["#MusicCommunity", "#BandLife", "#MusiciansDaily", "#OriginalMusic", "#IndieMusic"],
        "box3": ["#NowPlaying", "#MusicIsLife", "#StudioVibes", "#SoundtrackOfLife", "#ArtistDiscovery"]
    },
    "friendship_peer_support": {
        "keywords": [
            "friend", "friendship", "kindness", "kind to me", "shoutout", "proud of you", 
            "special to me", "support my", "grateful for you", "true friend", "best part of you",
            "beautiful lady", "stay true to you"
        ],
        "label": "Creative Collaboration & Peer Support",
        "box1": ["#TrueFriendship", "#GratefulHeart", "#FriendshipGoals", "#SupportYourFriends", "#KindnessMatters"],
        "box2": ["#LiftEachOtherUp", "#RealConnections", "#AppreciationPost", "#CommunityOverCompetition", "#GoodPeople"],
        "box3": ["#CelebrateOthers", "#AuthenticFriendships", "#PositiveVibes", "#LoyaltyAndLove", "#Heartfelt"]
    },
    "trauma_memoir_recovery": {
        "keywords": [
            "c-ptsd", "cptsd", "trauma", "memoir", "hypervigilance", "autobiography", 
            "grief", "recovery", "ptsd", "mental health", "healing", "traumas"
        ],
        "label": "Autobiographical Memoir & Trauma Recovery",
        "box1": ["#CPTSDAwareness", "#RadicalAuthenticity", "#TraumaRecovery", "#MentalResilience", "#RawHonesty"],
        "box2": ["#MentalHealthMatters", "#HealingJourney", "#OvercomingTrauma", "#InnerStrength", "#LifeAfterTrauma"],
        "box3": ["#Hypervigilance", "#MindsetShift", "#TruthHeals", "#ResilientMind", "#PersonalTransformation"]
    },
    "books_literature_writing": {
        "keywords": [
            "read my book", "my book", "new book", "novel", "author", "chapter", 
            "literature", "writer", "booktok", "bookstagram", "publishing", "publisher"
        ],
        "label": "Books, Literature & Author Craft",
        "box1": ["#IndieAuthor", "#MustRead", "#BookCommunity", "#AuthorsOfFacebook", "#Storytelling"],
        "box2": ["#BookLovers", "#Bibliophile", "#ReadersCommunity", "#NewBook", "#WritersLife"],
        "box3": ["#BookRecommendation", "#AmWriting", "#LiteratureLovers", "#PageTurner", "#AuthorJourney"]
    },
    "tech_software_engineering": {
        "keywords": [
            "code", "software", "daemon", "wsl", "gpu", "rtx", "fastapi", "react", 
            "ollama", "python", "hardware", "dev", "developer", "programming", 
            "github", "api", "fullstack", "frontend", "backend", "linux", "server"
        ],
        "label": "Software Engineering & Sovereign Tech",
        "box1": ["#OpenSource", "#SoftwareArchitecture", "#FullStackDev", "#IndieDev", "#DevLife"],
        "box2": ["#LocalLLM", "#TechFounders", "#PythonDev", "#BuildInPublic", "#SystemArchitecture"],
        "box3": ["#GPUComputing", "#EngineeringMindset", "#CodingLife", "#TechBuilder", "#ModernStack"]
    },
    "business_operations_growth": {
        "keywords": [
            "business", "revenue", "leads", "client", "sales", "enterprise", "commercial", 
            "pressure wash", "contractor", "roi", "operations", "marketing", "b2b"
        ],
        "label": "Commercial Growth & Enterprise Operations",
        "box1": ["#BusinessOperations", "#CommercialGrowth", "#Entrepreneurship", "#Leadership", "#LocalBusiness"],
        "box2": ["#LeadGeneration", "#ClientSuccess", "#B2BStrategy", "#BusinessMindset", "#SalesExecution"],
        "box3": ["#SmallBusinessOwner", "#OperationalExcellence", "#GrowthTactics", "#EnterpriseStrategy", "#ExecutionMatters"]
    },
    "fitness_health_wellness": {
        "keywords": [
            "workout", "gym", "fitness", "exercise", "lifting", "cardio", "training", 
            "health", "nutrition", "discipline", "bodybuilding", "wellness"
        ],
        "label": "Health, Fitness & Physical Wellness",
        "box1": ["#FitnessJourney", "#GymMotivation", "#HealthAndWellness", "#DisciplineEqualsFreedom", "#Consistency"],
        "box2": ["#FitLife", "#StrengthTraining", "#DailyWorkout", "#HealthyLifestyle", "#NeverGiveUp"],
        "box3": ["#TrainHard", "#MindAndBody", "#FitnessCommunity", "#GoalGetter", "#PeakPerformance"]
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
    """Detects primary topic strictly from text context and outbound URL."""
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
        
        # Domain bonus
        if target_url:
            u = target_url.lower()
            if key == "film_stage_arts" and ("imdb.com" in u or "filmfest" in u or "youtube.com" in u):
                score += 5
            elif key == "music_audio_performance" and ("spotify.com" in u or "soundcloud.com" in u or "bandcamp.com" in u):
                score += 5
            elif key == "tech_software_engineering" and ("github.com" in u or "gitlab.com" in u or "huggingface.co" in u):
                score += 5
            elif key == "books_literature_writing" and ("stehouwer-publishing.com" in u or "goodreads.com" in u or "/dp/" in u or "amazon.com" in u):
                score += 5
                
        scores[key] = score

    best_match = max(scores, key=scores.get)
    
    # Check if user explicitly wrote "stehouwer" in text
    user_mentioned_stehouwer = "stehouwer" in text_lower or (target_url and "stehouwer" in target_url.lower())

    if scores[best_match] == 0:
        box1 = ["#RadicalAuthenticity", "#PersonalGrowth", "#MindsetMatters", "#RealTalk", "#PerspectiveShift"]
        box2 = ["#SelfGrowth", "#StayTrueToYou", "#LifeLessons", "#AuthenticSelf", "#EverydayWisdom"]
        box3 = ["#SelfAwareness", "#InspireDaily", "#TruthTeller", "#MindsetShift", "#KeepMovingForward"]
        if user_mentioned_stehouwer:
            box1.append("#StehouwerPublishing")
            box3.append("#StehouwerPublishing")
        return {
            "key": "general_perspective",
            "label": "Personal Perspective & Real Talk",
            "box1": box1[:6],
            "box2": box2[:6],
            "box3": box3[:6]
        }
    
    match_data = TOPIC_CATALOG[best_match]
    box1 = list(match_data["box1"])
    box2 = list(match_data["box2"])
    box3 = list(match_data["box3"])

    # If the user mentioned a friend / support in a film or music post, enrich tags
    if best_match in ["film_stage_arts", "music_audio_performance"] and any(k in text_lower for k in ["friend", "support", "kind", "shoutout"]):
        if "#ArtistSpotlight" not in box3:
            box3[0] = "#ArtistSpotlight"
        if "#SupportYourFriends" not in box1:
            box1.append("#SupportYourFriends")

    # Only include brand tag if explicitly in the user input
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
    """Generates context-aware CTA based on topic and destination URL."""
    if not target_url:
        return {"long": "", "short": ""}
    
    url_lower = target_url.lower()
    
    if "imdb.com" in url_lower or topic_key == "film_stage_arts":
        return {
            "long": "\n\n(IMDb profile & credits pinned in the first comment 👇)",
            "short": "\n\n👉 IMDb profile & credits pinned in comment #1."
        }
    elif any(d in url_lower for d in ["spotify.com", "soundcloud.com", "bandcamp.com", "apple.com/music"]) or topic_key == "music_audio_performance":
        return {
            "long": "\n\n(Listen to track / stream pinned in the first comment 👇)",
            "short": "\n\n👉 Track link & stream pinned in comment #1."
        }
    elif topic_key == "books_literature_writing" or "book" in text_lower or "memoir" in text_lower or "author" in text_lower:
        return {
            "long": "\n\n(Book details & direct link pinned in the first comment 👇)",
            "short": "\n\n👉 Book details & link pinned in comment #1."
        }
    elif "github.com" in url_lower or topic_key == "tech_software_engineering":
        return {
            "long": "\n\n(Project repository & details pinned in the first comment 👇)",
            "short": "\n\n👉 Project code pinned in comment #1."
        }
    elif "youtube.com" in url_lower or "youtu.be" in url_lower or "vimeo.com" in url_lower:
        return {
            "long": "\n\n(Full video link pinned in the first comment 👇)",
            "short": "\n\n👉 Full video pinned in comment #1."
        }
    else:
        return {
            "long": "\n\n(Direct link & details pinned in the first comment 👇)",
            "short": "\n\n👉 Direct link pinned in comment #1."
        }

# Test with User's exact prompt from screenshot
user_text = """https://www.imdb.com/name/nm11231767/?ref_=nv_sr_srsg_0_tt_0_nm_8_in_0_q_anna%20stadler

No matter the role.
Always, Bad-Ass'. Support my 🎸☕️🎬
Click the link below.
Thank you for always finding time. 16 hour days on set or 20 hour days stage+ memorizing lines.
You always find the time to catch up. Please never give up being the beautiful lady you are.
Always stay true to you. If you forgot, being you, is the best part of you, the you, that was kind to me, became someone special, a friend to me."""

urls = extract_urls(user_text)
primary_url = urls[0] if urls else None
clean_text = strip_urls(user_text)
topic = detect_topic(user_text, primary_url)
cta = get_link_cta(topic["key"], primary_url, user_text.lower())

print("Detected Topic:", topic["label"])
print("Topic Key:", topic["key"])
print("CTA Long:", repr(cta["long"]).encode("ascii", "backslashreplace").decode("ascii"))
print("Box 1:", topic["box1"])
print("Box 2:", topic["box2"])
print("Box 3:", topic["box3"])
print("Stehouwer present?:", any("Stehouwer" in str(b) for b in [topic["box1"], topic["box2"], topic["box3"]]))

print("\n--- Test Case 2: Book Memoir Post ---")
book_text = """Are you, or have you ever had a moment where you wonder why I stand out in a cringe way...
read my book and learn about how I came this far and still have a long road ahead of me.
https://stehouwer-publishing.com/library"""

b_urls = extract_urls(book_text)
b_url = b_urls[0] if b_urls else None
b_topic = detect_topic(book_text, b_url)
b_cta = get_link_cta(b_topic["key"], b_url, book_text.lower())
print("Book Detected Topic:", b_topic["label"])
print("Book CTA Long:", repr(b_cta["long"]).encode("ascii", "backslashreplace").decode("ascii"))
print("Book Box 1:", b_topic["box1"])
print("Stehouwer present in book?:", any("Stehouwer" in str(b) for b in [b_topic["box1"], b_topic["box2"], b_topic["box3"]]))

print("\n--- Test Case 3: Pure General Post ---")
gen_text = "Life is all about showing up every single day and doing the work. You don't need anyone's validation. Keep going."
g_topic = detect_topic(gen_text, None)
print("Gen Detected Topic:", g_topic["label"])
print("Gen Box 1:", g_topic["box1"])
print("Stehouwer present in gen?:", any("Stehouwer" in str(b) for b in [g_topic["box1"], g_topic["box2"], g_topic["box3"]]))
