import re
from collections import Counter
from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile

from docx import Document
from pypdf import PdfReader
from pypdf.errors import PdfReadError

SKILLS = [
    "Python", "Java", "C", "C++", "JavaScript", "TypeScript", "React",
    "Node.js", "HTML", "CSS", "SQL", "MySQL", "PostgreSQL", "MongoDB",
    "Git", "GitHub", "Docker", "Machine Learning", "Deep Learning",
    "Artificial Intelligence", "Data Science", "Pandas", "NumPy",
    "TensorFlow", "PyTorch", "FastAPI", "Django", "Flask",
]

STOPWORDS = {
    "about", "after", "also", "and", "are", "been", "being", "both", "can", "candidate",
    "career", "company", "data", "description", "experience", "from", "have", "including",
    "into", "job", "more", "must", "other", "our", "role", "should", "team", "that", "their",
    "this", "through", "using", "with", "will", "within", "work", "working", "years", "your",
}

SECTIONS = (
    "experience", "work history", "education", "skills", "projects", "summary",
    "professional profile", "certifications",
)


def extract_resume(content: bytes, extension: str) -> tuple[str, list[str]]:
    if extension == ".pdf":
        try:
            reader = PdfReader(BytesIO(content), strict=True)
            return "\n".join(page.extract_text() or "" for page in reader.pages), []
        except (PdfReadError, OSError, ValueError) as error:
            raise ValueError("Invalid PDF resume") from error
    if extension == ".docx":
        try:
            document = Document(BytesIO(content))
            paragraphs = [paragraph.text for paragraph in document.paragraphs]
            layout_issues = []
            for table in document.tables:
                paragraphs.extend(cell.text for row in table.rows for cell in row.cells)
            if document.tables:
                layout_issues.append("Tables were detected; ATS parsers may read table-based content out of order.")
            if any(
                paragraph.text.strip()
                for section in document.sections
                for paragraph in [*section.header.paragraphs, *section.footer.paragraphs]
            ):
                layout_issues.append("Header or footer content was detected; keep essential contact details in the document body.")
            return "\n".join(paragraphs), layout_issues
        except (OSError, ValueError, KeyError, BadZipFile) as error:
            raise ValueError("Invalid DOCX resume") from error
    raise ValueError("Unsupported resume format")


def extract_resume_text(content: bytes, extension: str) -> str:
    return extract_resume(content, extension)[0]


def extract_skills(text: str) -> list[str]:
    found = []
    for skill in SKILLS:
        suffix_boundary = r"(?![\w+#])" if skill == "C" else r"(?!\w)"
        if re.search(rf"(?<!\w){re.escape(skill)}{suffix_boundary}", text, flags=re.IGNORECASE):
            found.append(skill)
    return found


def jd_keywords(job_description: str) -> list[str]:
    if not job_description.strip():
        return []
    known_skills = extract_skills(job_description)
    counts = Counter(
        word.casefold()
        for word in re.findall(r"[A-Za-z][A-Za-z+#.-]{2,}", job_description)
        if word.casefold() not in STOPWORDS
    )
    frequent_terms = [term for term, _ in counts.most_common(30) if counts[term] >= 2]
    return list(dict.fromkeys([*known_skills, *[term.title() for term in frequent_terms]]))[:20]


def contains_keyword(text: str, keyword: str) -> bool:
    suffix_boundary = r"(?![\w+#])" if keyword.casefold() == "c" else r"(?!\w)"
    return re.search(
        rf"(?<!\w){re.escape(keyword)}{suffix_boundary}",
        text,
        flags=re.IGNORECASE,
    ) is not None


def calculate_role_match(resume_text: str, keywords: list[str]) -> tuple[int, list[str]]:
    matched = [keyword for keyword in keywords if contains_keyword(resume_text, keyword)]
    missing = [keyword for keyword in keywords if keyword not in matched]
    score = round((len(matched) / len(keywords)) * 100) if keywords else 0
    return score, missing


def analyze_ats(
    resume_text: str,
    filename: str,
    keywords: list[str],
    layout_issues: list[str] | None = None,
) -> dict:
    text = resume_text.strip()
    lowered = text.casefold()
    words = re.findall(r"\b[\w+#.-]+\b", text)
    word_count = len(words)
    issues: list[str] = list(layout_issues or [])

    if word_count < 150:
        issues.append("Resume content is unusually short; include enough detail to show relevant experience.")
    if word_count > 1000:
        issues.append("Resume is lengthy; prioritize the most relevant information and keep it concise.")
    if not any(section in lowered for section in SECTIONS):
        issues.append("No standard section headings were detected (for example, Experience, Education, or Skills).")
    if not re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text):
        issues.append("No email address was detected in the resume text.")
    if not re.search(r"(?:\+?\d[\d\s().-]{7,}\d)", text):
        issues.append("No phone number was detected in the resume text.")
    if not re.search(r"(?m)^\s*(?:[-*•▪]|\d+[.)])\s+", text):
        issues.append("No recognizable list bullets were detected; use simple text bullets for experience.")
    long_paragraphs = [
        paragraph for paragraph in re.split(r"\n\s*\n", text)
        if len(re.findall(r"\b\w+\b", paragraph)) > 100
    ]
    if long_paragraphs:
        issues.append("One or more paragraphs are very dense; break them into concise, scannable bullets.")
    if Path(filename).suffix.casefold() not in {".pdf", ".docx"}:
        issues.append("Use a standard PDF or DOCX file format.")

    normalized_text = re.sub(r"\s+", " ", lowered)
    total_words = max(word_count, 1)
    heatmap = []
    for term in keywords[:20]:
        suffix_boundary = r"(?![\w+#])" if term.casefold() == "c" else r"(?!\w)"
        mentions = len(re.findall(
            rf"(?<!\w){re.escape(term.casefold())}{suffix_boundary}",
            normalized_text,
        ))
        density = mentions / total_words * 100
        status = "missing" if mentions == 0 else "low" if density < 0.5 else "high" if density > 3 else "within_benchmark"
        heatmap.append({
            "term": term,
            "mentions": mentions,
            "density_percent": round(density, 2),
            "benchmark_percent": "0.5-3.0",
            "status": status,
        })

    coverage = sum(item["mentions"] > 0 for item in heatmap) / max(len(heatmap), 1)
    structural_score = max(40, 100 - len(issues) * 10)
    score = round(structural_score * 0.7 + coverage * 100 * 0.3)
    return {
        "score": score,
        "word_count": word_count,
        "issues": issues,
        "keyword_heatmap": heatmap,
        "benchmark_note": "Keyword density is a heuristic (0.5-3.0% per term), not a universal ATS requirement.",
    }
