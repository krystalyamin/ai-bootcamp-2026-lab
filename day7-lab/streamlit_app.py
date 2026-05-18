"""
main.py — CLI entry point for the Day 4 Resume Analyzer.

Task 5 of the Day 4 lab (Track A).
Study material reference: §4 The Multi-Stage Pipeline

Your job is to write the main() function. The argument parser is already
provided — do not modify parse_args().
"""

import argparse
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


VALID_DEGREES = {"RTIS", "IMGD", "UXGD", "BFA"}
ATS_PASS_THRESHOLD = 60


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments. Pre-provided — do not modify.

    Usage:
        python main.py --resume path/to/resume.pdf \\
                       --jd     path/to/job_description.txt \\
                       --degree RTIS
    """
    parser = argparse.ArgumentParser(
        description="Day 4 Resume × JD Analyzer — diagnostic feedback only."
    )
    parser.add_argument(
        "--resume", required=True,
        help="Path to the PDF résumé."
    )
    parser.add_argument(
        "--jd", required=True,
        help="Path to the plain-text job description."
    )
    parser.add_argument(
        "--degree", required=True, choices=sorted(VALID_DEGREES),
        help="Your DigiPen degree code (RTIS | IMGD | UXGD | BFA)."
    )
    return parser.parse_args()


def main() -> int:
    """
    Orchestrate the full analysis pipeline. Return 0 on success, 1 on error.

    Steps to implement:
      [1/9] Parse CLI arguments (call parse_args()).
      [2/9] Load documents — call read_resume_pdf() and read_jd_text();
            catch ValueError and print to stderr, then return 1.
      [3/9] Extract structured profiles — call extract_resume_profile() and
            extract_jd_profile(); print progress as "[3/9] Extracting profiles…".
      [4/9] Run the 5 evaluations in order:
              analyse_keyword_match(resume_profile, jd_profile)
              analyse_bullets(resume_profile)
              analyse_jargon(resume_profile, args.degree, jd_profile)
              analyse_structure(resume_text)
              analyse_degree_alignment(jd_profile, args.degree)
            Print a [4/9]…[8/9] progress line for each.
      [9/9] Assemble the report dict:
              {
                "resume_profile":  resume_profile,
                "jd_profile":      jd_profile,
                "keyword_match":   keyword_match,
                "bullets":         bullets,
                "jargon":          jargon,
                "structure":       structure,
                "degree_alignment": degree_alignment,
              }
            Compute overall_score with compute_overall_score(report).
            Add to report:
              report["overall_score"]       = overall_score
              report["passes_ats_threshold"] = overall_score >= ATS_PASS_THRESHOLD
              report["summary"]             = summarise_overall(report)

            Build a timestamped filename:
              ts = datetime.now().strftime("%Y%m%d_%H%M%S")
              json_path = Path("outputs") / f"match_report_{ts}.json"
              md_path   = Path("outputs") / f"match_report_{ts}.md"

            Save JSON: json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
            Save Markdown: render_markdown(report, out_path=md_path)

            Print the final verdict and the 3-bullet summary.
            Return 0.
    """
    st.title("Resume Analyzer")

    # Initialise session state flags
    if "submitted" not in st.session_state:
        st.session_state.submitted = False
    if "degree" not in st.session_state:
        st.session_state.degree = ""
    if "resume_text" not in st.session_state:
        st.session_state.resume_text = ""
    if "jd_text" not in st.session_state:
        st.session_state.jd_text = ""

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
    jd_text = ""
    uploaded_jd = st.file_uploader("Upload Job Description", type=["txt"])
    if uploaded_jd is not None:
        try:
            jd_text = read_jd_text(uploaded_jd)
            st.session_state.jd_text = jd_text
        except ValueError as e:
            st.exception(e)
            print(e, file=sys.stderr)
            return 1

    # Every form must have a submit button.
    all_ready = (
        degree.strip() != ""
        and st.session_state.resume_text != ""
        and st.session_state.jd_text != ""
    )
    print("can submit: ", all_ready)
    submitted = st.button("Analyse Resume", disabled=not all_ready)
    if submitted:
        st.session_state.submitted = True

    if st.session_state.submitted:

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
    
        # [5/9] Bullet quality
        current_steps += 1.0
        progress_bar.progress((current_steps/TOTAL_STEPS), "Analysing bullet quality…")
        print("[5/9] Analysing bullet quality…")
        bullets = analyse_bullets(resume_profile)
    
        # [6/9] Jargon audit
        current_steps += 1.0
        progress_bar.progress((current_steps/TOTAL_STEPS), "Auditing jargon…")
        print("[6/9] Auditing jargon…")
        jargon = analyse_jargon(resume_profile, degree, jd_profile)
    
        # [7/9] Structure audit
        current_steps += 1.0
        progress_bar.progress((current_steps/TOTAL_STEPS), "Auditing structure…")
        print("[7/9] Auditing structure…")
        structure = analyse_structure(resume_text)
    
        # [8/9] Degree alignment
        current_steps += 1.0
        progress_bar.progress((current_steps/TOTAL_STEPS), "Analysing degree alignment…")
        print("[8/9] Analysing degree alignment…")
        degree_alignment = analyse_degree_alignment(jd_profile, degree)
    
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
        json_path = Path("outputs") / f"match_report_{ts}.json"
        md_path   = Path("outputs") / f"match_report_{ts}.md"
    
        progress_bar.empty()

        # Save outputs
        json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        render_markdown(report, out_path=md_path)
    
        # Print final verdict and summary
        verdict = "PASSES" if report["passes_ats_threshold"] else "DOES NOT PASS"
        st.info(f"\nOverall Score: {overall_score}/100 — {verdict} ATS threshold ({ATS_PASS_THRESHOLD})")
        st.info(f"\nSummary:\n{report['summary']}")
        # st.info(f"\nReports saved to:\n  {json_path}\n  {md_path}")

        json_str = json.dumps(report, indent=2)
        md_str   = md_path.read_text(encoding="utf-8")

        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="Download JSON Report",
                data=json_str,
                file_name=json_path.name,
                mime="application/json",
            )
        with col2:
            st.download_button(
                label="Download Markdown Report",
                data=md_str,
                file_name=md_path.name,
                mime="text/markdown",
            )
 
    return 0


if __name__ == "__main__":
    sys.exit(main())
