import pymupdf4llm
import re


def extract_text_from_pdf(file_path: str) -> str:
    try:
        md_text = pymupdf4llm.to_markdown(file_path)
        return md_text if md_text.strip() else "Empty PDF"
    except Exception as e:
        return f"Error: {str(e)}"


def is_likely_name(text: str) -> bool:
    """Check if a string looks like a person's name"""
    text = text.strip()

    # Length check — names are usually 3-30 chars
    if len(text) < 3 or len(text) > 30:
        return False

    # Must not contain these
    bad_chars = ['@', '|', '/', '\\', '+', '=', '_', '(', ')', '[', ']']
    if any(c in text for c in bad_chars):
        return False

    # Must not start with number
    if text[0].isdigit():
        return False

    # Skip words that are NOT names
    skip_words = [
    "summary", "objective", "profile", "about", "overview",
    "experience", "education", "skills", "projects", "certif",
    "award", "language", "reference", "declaration", "contact",
    "phone", "email", "mobile", "address", "linkedin", "github",
    "portfolio", "website", "intern", "remote", "india", "mumbai",
    "delhi", "bangalore", "hyderabad", "pune", "chennai", "kolkata",
    "nagar", "city", "street", "road", "area", "sector", "block",
    "junior", "senior", "lead", "manager", "engineer", "developer",
    "analyst", "designer", "consultant", "fresher", "experienced",
    "year", "month", "present", "current", "page", "curriculum",
    "vitae", "resume", "cv", "dear", "sir", "madam", "hiring",
    # ← ADD THESE NEW ONES:
    "incubation", "cell", "center", "centre", "institute", "college",
    "university", "school", "department", "division", "committee",
    "association", "club", "society", "foundation", "organization",
    "company", "corporation", "pvt", "ltd", "llc", "inc",
    "technology", "technologies", "solutions", "services", "systems"
]
    text_lower = text.lower()
    if any(w in text_lower for w in skip_words):
        return False

    # Skip if too many numbers
    digit_count = sum(c.isdigit() for c in text)
    if digit_count > 2:
        return False

    # Skip if URL-like
    if re.search(r'http|www|\.com|\.in|\.org|\.net', text_lower):
        return False

    # Skip if looks like location (has comma + known city/state pattern)
    if re.search(r',\s*[A-Z][a-z]+$', text):
        return False

    # Skip if all uppercase and more than 3 words (likely a heading)
    words = text.split()
    if len(words) > 3 and text == text.upper():
        return False

    # Must have at least one letter
    if not any(c.isalpha() for c in text):
        return False

    # Good — looks like a name
    return True


def parse_resume_with_claude(text: str) -> dict:
    """Basic parser using regex — no API key needed"""

    # Extract email
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    email = email_match.group(0) if email_match else ""

    # Extract phone
    phone_match = re.search(r'[\+\(]?[0-9][0-9\s\-\(\)]{7,}[0-9]', text)
    phone = phone_match.group(0).strip() if phone_match else ""

    # Extract name using smart detection
    name = "Unknown"
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    for line in lines[:25]:
        # Clean markdown
        clean = re.sub(r'[#*_\-•]', '', line).strip()
        clean = re.sub(r'\s+', ' ', clean).strip()

        if is_likely_name(clean):
            name = clean
            break

    # Extract skills
    skill_keywords = [
        "Python", "JavaScript", "React", "Node", "FastAPI", "Django",
        "SQL", "PostgreSQL", "MySQL", "MongoDB", "Docker", "Git",
        "AWS", "Azure", "Machine Learning", "AI", "Java", "C++",
        "TypeScript", "HTML", "CSS", "REST", "API", "Linux",
        "Flutter", "Kotlin", "Swift", "PHP", "Laravel", "Vue",
        "TensorFlow", "PyTorch", "Pandas", "NumPy", "Scikit",
        "Redis", "Kafka", "GraphQL", "Spring", "Angular", "Next.js"
    ]
    found_skills = [s for s in skill_keywords if s.lower() in text.lower()]

    return {
        "candidate_name": name,
        "email": email,
        "phone": phone,
        "summary": "Experienced professional with relevant skills.",
        "skills": found_skills,
        "experience": [
            {
                "company": "See Resume",
                "role": "Professional",
                "duration": "N/A",
                "description": "Please view full resume for details"
            }
        ],
        "education": [
            {
                "degree": "See Resume",
                "institution": "See Resume",
                "year": "N/A"
            }
        ]
    }