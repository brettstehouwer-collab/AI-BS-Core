import re

def format_personalized_message(template: str, recipient: dict) -> str:
    name = (recipient.get("name") or "").strip()
    if not name or name.lower() in ("direct contact", "student-athlete", "n/a", "none"):
        full_name = "Student-Athlete"
        first_name = "Student-Athlete"
    else:
        full_name = name
        first_name = name.split()[0]

    high_school = (recipient.get("high_school") or recipient.get("school") or "").strip() or "your high school"
    sport = (recipient.get("sport") or "").strip() or "Basketball"
    grad_year = str(recipient.get("grad_year") or recipient.get("year") or "").strip() or "2026"

    formatted = template

    # Case-insensitive replacement for name tags with spaces, underscores, or hyphens
    formatted = re.sub(r'\{(?i:athlete[\s_-]*name|full[\s_-]*name|name)\}|\[(?i:athlete[\s_-]*name|full[\s_-]*name|name)\]|\((?i:athlete[\s_-]*name|full[\s_-]*name|name)\)', full_name, formatted)
    formatted = re.sub(r'\{(?i:first[\s_-]*name|firstname|first)\}|\[(?i:first[\s_-]*name|firstname|first)\]|\((?i:first[\s_-]*name|firstname|first)\)', first_name, formatted)
    formatted = re.sub(r'\{(?i:last[\s_-]*name|lastname|last)\}|\[(?i:last[\s_-]*name|lastname|last)\]|\((?i:last[\s_-]*name|lastname|last)\)', recipient.get("name", "").split()[-1] if recipient.get("name") else "", formatted)
    formatted = re.sub(r'\{(?i:high[\s_-]*school|highschool|school)\}|\[(?i:high[\s_-]*school|highschool|school)\]', high_school, formatted)
    formatted = re.sub(r'\{(?i:sport)\}|\[(?i:sport)\]', sport, formatted)
    formatted = re.sub(r'\{(?i:grad[\s_-]*year|graduation[\s_-]*year|gradyear|class[\s_-]*of|class|year)\}|\[(?i:grad[\s_-]*year|graduation[\s_-]*year|gradyear|class[\s_-]*of|class|year)\]', grad_year, formatted)

    # Check if a greeting exists in the first 150 chars
    has_name_greeting = bool(re.search(
        rf'\b(hi|hey|hello|dear|greetings|good\s+(?:morning|afternoon|evening))\b',
        formatted[:150],
        re.IGNORECASE
    ))

    # Prepend personalized greeting only if no greeting already exists in the text
    if not has_name_greeting and full_name != "Student-Athlete":
        formatted = f"Hey {first_name},\n\n{formatted}"

    return formatted


sample = {
    "name": "Amerria Crowley",
    "high_school": "Hardaway High School",
    "sport": "Basketball",
    "grad_year": "2027"
}

t1 = "Hi {NAME}, Dennis Bell here from Recreational Debut. We are watching your progress at {school}."
t2 = "This is Dennis Bell from Recreational Debut. We scouted you at {school} for the Class of {grad_year}."
t3 = "Dear [Athlete Name], congratulations on your {sport} season at [high_school]."
t4 = "Hey {first_name}, how is training going for Class of {grad_year}?"

print("--- Test 1 (Template has 'Hi {NAME},') ---")
print(format_personalized_message(t1, sample))

print("\n--- Test 2 (Template has NO greeting) ---")
print(format_personalized_message(t2, sample))

print("\n--- Test 3 (Template has 'Dear [Athlete Name],') ---")
print(format_personalized_message(t3, sample))

print("\n--- Test 4 (Template has 'Hey {first_name},') ---")
print(format_personalized_message(t4, sample))
