import re


def analyze_ats(resume_text: str) -> dict:
    """Smarter ATS scorer with varied scores"""

    text_lower = resume_text.lower()
    score = 30  # base score

    # ── Content Checks ─────────────────────────
    # Contact info
    if re.search(r'[\w\.-]+@[\w\.-]+\.\w+', resume_text):     score += 8
    if re.search(r'[\+\(]?[0-9][0-9\s\-\(\)]{8,}[0-9]', resume_text): score += 5
    if re.search(r'linkedin\.com', text_lower):                score += 4
    if re.search(r'github\.com', text_lower):                  score += 4

    # Sections
    if re.search(r'summary|objective|profile|about', text_lower):  score += 6
    if re.search(r'experience|work history|employment', text_lower): score += 8
    if re.search(r'education|degree|university|college', text_lower): score += 6
    if re.search(r'skills|technologies|tools|expertise', text_lower): score += 6
    if re.search(r'project|portfolio|built|developed', text_lower):  score += 5
    if re.search(r'certif|award|achievement|accomplishment', text_lower): score += 4

    # ── Quality Checks ──────────────────────────
    # Numbers and metrics (shows impact)
    numbers = re.findall(r'\d+[\%\+]?', resume_text)
    if len(numbers) > 10: score += 5
    elif len(numbers) > 5: score += 3

    # Action verbs
    action_verbs = ["developed", "built", "led", "managed", "created",
                    "designed", "implemented", "improved", "increased",
                    "reduced", "launched", "delivered", "achieved"]
    verb_count = sum(1 for v in action_verbs if v in text_lower)
    if verb_count >= 5:   score += 5
    elif verb_count >= 3: score += 3

    # Resume length (too short is bad)
    word_count = len(resume_text.split())
    if word_count > 400:   score += 4
    elif word_count > 200: score += 2
    elif word_count < 100: score -= 10

    # Skills count
    skill_keywords = [
        "python", "javascript", "react", "node", "fastapi", "django",
        "sql", "postgresql", "mysql", "mongodb", "docker", "git",
        "aws", "azure", "machine learning", "ai", "java", "c++",
        "typescript", "html", "css", "rest", "api", "linux",
        "flutter", "kotlin", "swift", "php", "laravel", "vue"
    ]
    skill_count = sum(1 for s in skill_keywords if s in text_lower)
    if skill_count >= 8:   score += 6
    elif skill_count >= 5: score += 4
    elif skill_count >= 3: score += 2

    # ── Penalties ───────────────────────────────
    if word_count < 150:                    score -= 8   # too short
    if not re.search(r'@', resume_text):    score -= 10  # no email
    if skill_count == 0:                    score -= 5   # no skills

    # Keep score in range 20-94
    score = max(20, min(94, score))

    # Sub scores
    keyword_score  = max(20, min(95, score - 5 + (skill_count * 2)))
    format_score   = max(20, min(95, score + 3 if word_count > 300 else score - 5))
    exp_score      = max(20, min(95, score - 3 if verb_count < 3 else score + 2))

    # Build feedback based on actual resume
    strengths = []
    improvements = []
    missing = []

    if re.search(r'@', resume_text):
        strengths.append("Contact email is present")
    if re.search(r'linkedin', text_lower):
        strengths.append("LinkedIn profile included")
    if re.search(r'github', text_lower):
        strengths.append("GitHub profile included")
    if verb_count >= 3:
        strengths.append("Good use of action verbs")
    if skill_count >= 5:
        strengths.append(f"{skill_count} technical skills detected")
    if re.search(r'project', text_lower):
        strengths.append("Projects section found")
    if not strengths:
        strengths.append("Resume uploaded successfully")

    if not re.search(r'summary|objective', text_lower):
        improvements.append("Add a professional summary section")
    if verb_count < 3:
        improvements.append("Use more action verbs (built, led, developed)")
    if len(numbers) < 3:
        improvements.append("Add quantified achievements (e.g. improved speed by 30%)")
    if not re.search(r'linkedin', text_lower):
        improvements.append("Add your LinkedIn profile URL")
    if not re.search(r'certif', text_lower):
        improvements.append("Add certifications if you have any")
    if word_count < 300:
        improvements.append("Resume seems short — add more details")

    if not re.search(r'github', text_lower):
        missing.append("GitHub profile link")
    if not re.search(r'certif', text_lower):
        missing.append("Certifications")
    if len(numbers) < 5:
        missing.append("Quantified achievements with numbers")
    if not re.search(r'project', text_lower):
        missing.append("Projects section")
    if not missing:
        missing.append("Consider adding portfolio link")

    return {
        "ats_score": float(score),
        "keyword_score": keyword_score,
        "format_score": format_score,
        "experience_score": exp_score,
        "strengths": strengths[:4],
        "missing_keywords": missing[:4],
        "improvements": improvements[:4],
        "optimized_summary": "Connect Claude/Gemini API for AI-generated summary."
    }