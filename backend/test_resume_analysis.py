from io import BytesIO

import pytest
from docx import Document

from resume_analysis import (
    analyze_ats,
    calculate_role_match,
    extract_resume,
    extract_resume_text,
    extract_skills,
    jd_keywords,
)


def test_extracts_docx_paragraphs_and_table_content():
    document = Document()
    document.add_paragraph("Python developer")
    document.add_table(rows=1, cols=1).cell(0, 0).text = "FastAPI"
    output = BytesIO()
    document.save(output)

    text, layout_issues = extract_resume(output.getvalue(), ".docx")
    assert "Python developer" in text
    assert "FastAPI" in text
    assert any("Tables were detected" in issue for issue in layout_issues)


@pytest.mark.parametrize(
    ("content", "extension"),
    [(b"not a pdf", ".pdf"), (b"not a docx", ".docx"), (b"anything", ".txt")],
)
def test_rejects_malformed_or_unsupported_resume(content, extension):
    with pytest.raises(ValueError):
        extract_resume_text(content, extension)


def test_skill_matching_respects_word_boundaries():
    assert extract_skills("Experience with C++, SQL, and Python.") == ["Python", "C++", "SQL"]
    assert "C" not in extract_skills("CSS specialist")


def test_jd_keywords_and_role_match():
    keywords = jd_keywords("Python Python API SQL SQL Docker Docker")
    assert "Python" in keywords
    score, missing = calculate_role_match("Built APIs in Python", ["Python", "SQL"])
    assert score == 50
    assert missing == ["SQL"]
    score, missing = calculate_role_match("C++ developer", ["C", "C++"])
    assert score == 50
    assert missing == ["C"]


def test_ats_score_and_keyword_heatmap_are_bounded_and_explainable():
    result = analyze_ats(
        "Experience\n" + " ".join(["Python"] * 4) + "\n- Delivered a service",
        "resume.pdf",
        ["Python", "SQL"],
    )
    assert 0 <= result["score"] <= 100
    assert result["keyword_heatmap"][0]["status"] == "high"
    assert result["keyword_heatmap"][1]["status"] == "missing"
    assert result["issues"]
