import pymupdf4llm
import re
import os
from app.services.llm import ask_claude_json, llm_available


def extract_text_from_pdf(file_path: str) -> str:
    try:
        md_text = pymupdf4llm.to_markdown(file_path)
        return md_text if md_text.strip() else "Empty PDF"
    except Exception as e:
        return f"Error: {str(e)}"


def is_likely_name(text: str) -> bool:
    """Check if a string looks like a person's name"""
    text = text.strip()

    if len(text) < 3 or len(text) > 30:
        return False

    if text.endswith((".", ",", ":", ";", "!", "?")):
        return False

    words = text.split()
    if not words or not words[0][0].isupper():
        return False

    bad_chars = ['@', '|', '/', '\\', '+', '=', '_', '(', ')', '[', ']']
    if any(c in text for c in bad_chars):
        return False

    if text[0].isdigit():
        return False

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
        "incubation", "cell", "center", "centre", "institute", "college",
        "university", "school", "department", "division", "committee",
        "association", "club", "society", "foundation", "organization",
        "company", "corporation", "pvt", "ltd", "llc", "inc",
        "technology", "technologies", "solutions", "services", "systems",
        "recommendation", "relevance", "achievement", "responsibility",
        "description", "intermediate", "matriculation", "gmail"
    ]
    text_lower = text.lower()
    if any(w in text_lower for w in skip_words):
        return False

    digit_count = sum(c.isdigit() for c in text)
    if digit_count > 2:
        return False

    if re.search(r'http|www|\.com|\.in|\.org|\.net', text_lower):
        return False

    if re.search(r',\s*[A-Z][a-z]+$', text):
        return False

    words = text.split()
    if len(words) > 3 and text == text.upper():
        return False

    if not any(c.isalpha() for c in text):
        return False

    return True


def parse_resume_with_regex(text: str, filename: str = "") -> dict:
    """Heuristic fallback parser — no API needed (original mock parser)"""

    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    email = email_match.group(0) if email_match else ""

    phone_match = re.search(r'[\+\(]?[0-9][0-9\s\-\(\)]{7,}[0-9]', text)
    phone = phone_match.group(0).strip() if phone_match else ""

    name = "Unknown"
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    for line in lines[:25]:
        clean = re.sub(r'[#*_\-•]', '', line).strip()
        clean = re.sub(r'\s+', ' ', clean).strip()
        if is_likely_name(clean):
            name = clean
            break

    # Fallback: derive name from filename
    if name == "Unknown" and filename:
        base = os.path.splitext(filename)[0]
        base = re.sub(r'^\d+_', '', base)
        base = re.sub(r'[\[\(].*?[\]\)]', '', base)
        base = re.sub(r'[\[\]\(\)\d]', '', base)
        cleaned = base.replace("_", " ").replace("-", " ")
        cleaned = re.sub(r'\b(resume|cv|final|updated|new|copy)\b', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        if cleaned and len(cleaned) >= 3:
            name = cleaned.title()

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
        "experience": [{"company": "See Resume", "role": "Professional",
                        "duration": "N/A", "description": "Please view full resume for details"}],
        "education": [{"degree": "See Resume", "institution": "See Resume", "year": "N/A"}]
    }


def parse_resume_with_claude(text: str, filename: str = "") -> dict:
    """Primary parser: Claude API with structured JSON output.
    Falls back to regex heuristics automatically on any failure."""

    if not llm_available:
        return parse_resume_with_regex(text, filename)

    try:
        system = (
            "You are an expert resume parser. Extract structured data from resume text. "
            "Respond with ONLY a valid JSON object — no markdown, no explanation, no code fences."
        )
        prompt = f"""Extract the following from this resume and return ONLY JSON in exactly this schema:
{{
  "candidate_name": "full name of the person",
  "email": "email address or empty string",
  "phone": "phone number or empty string",
  "summary": "2-sentence professional summary based on the resume content",
  "skills": ["skill1", "skill2", ...],
  "experience": [{{"company": "...", "role": "...", "duration": "...", "description": "one line"}}],
  "education": [{{"degree": "...", "institution": "...", "year": "..."}}]
}}

Rules:
- candidate_name must be a real person's name, never a heading or sentence fragment
- skills: max 15, actual technical/professional skills only
- experience/education: max 4 entries each; empty list if none found

RESUME TEXT:
{text[:6000]}"""

        parsed = ask_claude_json(prompt, system=system, max_tokens=1500)

        # Sanity checks — fall back if the response is malformed
        if not isinstance(parsed, dict) or not parsed.get("candidate_name"):
            raise ValueError("Malformed LLM response")

        # Guarantee all keys exist with safe defaults
        parsed.setdefault("email", "")
        parsed.setdefault("phone", "")
        parsed.setdefault("summary", "")
        parsed.setdefault("skills", [])
        parsed.setdefault("experience", [])
        parsed.setdefault("education", [])

        print(f"✅ Parsed with Claude API: {parsed['candidate_name']}")
        return parsed

    except Exception as e:
        print(f"⚠️ Claude parsing failed ({e}) — using regex fallback")
        return parse_resume_with_regex(text, filename)