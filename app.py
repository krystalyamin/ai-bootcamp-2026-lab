"""
streamlit_app.py — Entry point for the Resume Analyzer.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

from parse import read_resume_pdf, read_jd_text
from analyzer import (
    extract_resume_profile,
    extract_jd_profile,
    analyse_keyword_match,
    analyse_bullets,
    analyse_jargon,
    analyse_structure,
    analyse_degree_alignment,
    summarise_overall,
    compute_overall_score,
)
from report import render_markdown
import streamlit as st
from renderer import (
    render_keyword_analysis,
    render_bullet_analysis,
    render_jargon_analysis,
    render_structure_analysis,
    render_degree_analysis
)

VALID_DEGREES = {"RTIS", "IMGD", "UXGD", "BFA"}
ATS_PASS_THRESHOLD = 60

def analyse_files(degree: str, resume_text: str, jd_text: str) -> None:
    """
    Analyses the provided text content step by step.
    Draws the progress bar UI and outputs a report.
    """
    
    # [3/9] Extract structured profiles
    print("[3/9] Extracting profiles…")
    current_steps = 0.0
    TOTAL_STEPS = 8.0
    progress_bar = st.progress(0.0, text="Files uploaded! Extracting resume details...")
    resume_profile = extract_resume_profile(resume_text)

    current_steps += 1.0
    progress_bar.progress(current_steps/TOTAL_STEPS, "Extracting job description details...")
    jd_profile = extract_jd_profile(jd_text)

    # [4/9] Keyword match    
    current_steps += 1.0
    progress_bar.progress((current_steps/TOTAL_STEPS), "Analysing keyword match…")
    print("[4/9] Analysing keyword match…")
    keyword_match = analyse_keyword_match(resume_profile, jd_profile)
    render_keyword_analysis(keyword_match)
    st.divider()

    # [5/9] Bullet quality
    current_steps += 1.0
    progress_bar.progress((current_steps/TOTAL_STEPS), "Analysing bullet quality…")
    print("[5/9] Analysing bullet quality…")
    bullets = analyse_bullets(resume_profile)
    render_bullet_analysis(bullets)
    st.divider()

    # [6/9] Jargon audit
    current_steps += 1.0
    progress_bar.progress((current_steps/TOTAL_STEPS), "Auditing jargon…")
    print("[6/9] Auditing jargon…")
    jargon = analyse_jargon(resume_profile, degree, jd_profile)
    render_jargon_analysis(jargon)
    st.divider()

    # [7/9] Structure audit
    current_steps += 1.0
    progress_bar.progress((current_steps/TOTAL_STEPS), "Auditing structure…")
    print("[7/9] Auditing structure…")
    structure = analyse_structure(resume_text)
    render_structure_analysis(structure)
    st.divider()

    # [8/9] Degree alignment
    current_steps += 1.0
    progress_bar.progress((current_steps/TOTAL_STEPS), "Analysing degree alignment…")
    print("[8/9] Analysing degree alignment…")
    degree_alignment = analyse_degree_alignment(jd_profile, degree)
    render_degree_analysis(degree_alignment)
    st.divider()

    # [9/9] Assemble report
    current_steps += 1.0
    progress_bar.progress((current_steps/TOTAL_STEPS), "Assembling report…")
    report = {
        "resume_profile":   resume_profile,
        "jd_profile":       jd_profile,
        "keyword_match":    keyword_match,
        "bullets":          bullets,
        "jargon":           jargon,
        "structure":        structure,
        "degree_alignment": degree_alignment,
    }

    overall_score = compute_overall_score(report)
    report["overall_score"]        = overall_score
    report["passes_ats_threshold"] = overall_score >= ATS_PASS_THRESHOLD
    report["summary"]              = summarise_overall(report)

    # Build timestamped output paths
    Path("outputs").mkdir(exist_ok=True)
    ts        = datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state.json_path = Path("outputs") / f"match_report_{ts}.json"
    st.session_state.md_path   = Path("outputs") / f"match_report_{ts}.md"

    progress_bar.empty()

    # Save outputs
    st.session_state.json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    render_markdown(report, out_path=st.session_state.md_path)

    # Print final verdict and summary
    verdict = "PASSES" if report["passes_ats_threshold"] else "DOES NOT PASS"
    if report["passes_ats_threshold"]:
        st.success(f"\nOverall Score: {overall_score}/100 — {verdict} ATS threshold ({ATS_PASS_THRESHOLD})")
    else:
        st.error(f"\nOverall Score: {overall_score}/100 — {verdict} ATS threshold ({ATS_PASS_THRESHOLD})")

    st.info(f"\nSummary:\n{report['summary']}")

    # Buttons to download the reports
    st.session_state.json_str = json.dumps(report, indent=2)
    st.session_state.md_str   = st.session_state.md_path.read_text(encoding="utf-8")
    st.session_state.done = True


def reset_vars() -> None:
    """
    Initialize all the session state variables.
    """
    # Initialise session state flags
    if "submitted" not in st.session_state:
        st.session_state.submitted = False
    if "done" not in st.session_state:
        st.session_state.done = False
    if "degree" not in st.session_state:
        st.session_state.degree = ""
    if "resume_text" not in st.session_state:
        st.session_state.resume_text = ""
    if "jd_text" not in st.session_state:
        st.session_state.jd_text = ""
    if "json_path" not in st.session_state:
        st.session_state.json_path = ""
    if "md_path" not in st.session_state:
        st.session_state.md_path = ""
    if "json_str" not in st.session_state:
        st.session_state.json_str = ""
    if "md_str" not in st.session_state:
        st.session_state.md_str = ""

def main() -> int:
    """
    Orchestrate the full analysis pipeline. Return 0 on success, 1 on error.
    Print the final verdict and the 3-bullet summary.
    """
    st.title("Resume Analyzer")
    reset_vars()

    # [1/9] Accept and load Resume and degree
    degree = st.text_input("Degree Programme", value="RTIS")
    degree = degree.strip()
    st.session_state.degree = degree

    resume_text = ""
    uploaded_resume = st.file_uploader("Upload Resume", type=["pdf"])
    if uploaded_resume is not None:
        try:
            resume_text = read_resume_pdf(uploaded_resume)
            st.session_state.resume_text = resume_text
        except ValueError as e:
            st.exception(e)
            print(e, file=sys.stderr)
            return 1

    # [2/9] Accept and load job desc
    jd_text = st.text_area("Upload Job Description")
    st.session_state.jd_text = jd_text

    # Every form must have a submit button.
    all_ready = (
        degree.strip() != ""
        and st.session_state.resume_text != ""
        and st.session_state.jd_text != ""
    )
    print("can submit: ", all_ready)

    submitted = st.button("Analyse Resume", disabled=not all_ready)

    if submitted and not st.session_state.submitted:
        st.session_state.submitted = True        
        if st.session_state.submitted and not st.session_state.done:
            st.divider()
            analyse_files(st.session_state.degree, st.session_state.resume_text, st.session_state.jd_text)
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="Download JSON Report",
                    data=st.session_state.json_str,
                    file_name=st.session_state.json_path.name,
                    mime="application/json",
                )
            with col2:
                st.download_button(
                    label="Download Markdown Report",
                    data=st.session_state.md_str,
                    file_name=st.session_state.md_path.name,
                    mime="text/markdown",
                )
    return 0


if __name__ == "__main__":
    sys.exit(main())
