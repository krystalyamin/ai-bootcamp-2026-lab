"""
Functions for rendering the output of individual stages of the resume analysis.
"""
import streamlit as st
import pandas as pd


# For keyword analysis
CATEGORY_COLORS = {
    "language":   ("#dbeafe", "#1d4ed8"),   # blue
    "framework":  ("#ede9fe", "#6d28d9"),   # purple
    "tool":       ("#fef9c3", "#a16207"),   # yellow
    "concept":    ("#dcfce7", "#15803d"),   # green
    "soft_skill": ("#ffedd5", "#c2410c"),   # orange
    "buzzword":   ("#fce7f3", "#9d174d"),   # pink
}

IMPORTANCE_COLORS = {
    "required":  ("#fee2e2", "#b91c1c"),    # red
    "preferred": ("#fef9c3", "#a16207"),    # yellow
}


# For bullet point analysis
LEVEL_CONFIG = {
    "L1_OK":    {"bg": "#fee2e2", "fg": "#b91c1c", "label": "L1 · OK"    },
    "L2_BETTER":{"bg": "#fef9c3", "fg": "#a16207", "label": "L2 · Better"},
    "L3_BEST":  {"bg": "#dcfce7", "fg": "#15803d", "label": "L3 · Best"  },
}

SOURCE_COLORS = {
    "projects":   ("#ede9fe", "#6d28d9"),
    "experience": ("#dbeafe", "#1d4ed8"),
}
 
SCORE_THRESHOLDS = [
    (2.5, "#15803d", "#dcfce7"),
    (1.5, "#a16207", "#fef9c3"),
    (0,   "#b91c1c", "#fee2e2"),
]

CHECK_FIELDS = [
    ("has_action_verb",        "Action verb"),
    ("has_specific_technology","Specific tech"),
    ("has_measurable_impact",  "Measurable impact"),
]

ATS_PASS_THRESHOLD = 60
JARGON_PASS_THRESHOLD = 30


# ----- HELPER FUNCTIONS -------------------------------------------------

def _badge(text: str, bg: str, fg: str) -> str:
    """Return an HTML pill badge."""
    style = (
        f"background:{bg};color:{fg};padding:2px 10px;"
        "border-radius:999px;font-size:0.75rem;font-weight:600;"
        "white-space:nowrap;display:inline-block;"
    )
    return f'<span style="{style}">{text}</span>'


def _category_badge(category: str) -> str:
    bg, fg = CATEGORY_COLORS.get(category, ("#e5e7eb", "#374151"))
    return _badge(category, bg, fg)


def _importance_badge(importance: str) -> str:
    bg, fg = IMPORTANCE_COLORS.get(importance, ("#e5e7eb", "#374151"))
    return _badge(importance, bg, fg)


def _exact_match_badge(exact: bool) -> str:
    if exact:
        return _badge("exact", "#dcfce7", "#15803d")
    return _badge("partial", "#fef9c3", "#a16207")


def _bool_badge(value: bool) -> str:
    return "Yes" if value else "No"


def _level_badge(level: str) -> str:
    level_map = {
        "L1_OK": "L1 - OK",
        "L2_BETTER": "L2 - Better",
        "L3_BEST": "L3 - Best",
    }
    return level_map.get(level, level)



# ----- RENDER FUNCTIONS -------------------------------------------------

def render_keyword_analysis(data: dict) -> None:
    """
    Render a keyword-match analysis dict produced by an ATS/resume tool.
    """

    present: list[dict] = data.get("present", [])
    missing: list[dict] = data.get("missing", [])
    score:   int        = int(data.get("keyword_match_score", 0))

    if score >= ATS_PASS_THRESHOLD:
        st.success(f"Keyword Match Score: {score} (STRONG)")
    else:
        st.error(f"Keyword Match Score: {score} (WEAK)")
    tab_present, tab_missing = st.tabs(
        [f"Present ({len(present)})", f"Missing ({len(missing)})"]
    )

    # Display tabs for keywords that are present and missing
    # PRESENT keywords
    with tab_present:
        if not present:
            st.info("No matching keywords found.")
        else:
            rows = []
            for item in present:
                rows.append(
                    {
                        "Keyword":  item.get("keyword", ""),
                        "Category": _category_badge(item.get("category", "")),
                        "Found in": item.get("found_in", ""),
                        "Match":    _exact_match_badge(item.get("exact_match", False)),
                    }
                )
            df = pd.DataFrame(rows)
            st.markdown(
                df.to_html(escape=False, index=False),
                unsafe_allow_html=True,
            )

    # MISSING keywords
    with tab_missing:
        if not missing:
            st.success("No missing keywords — great coverage!")
        else:
            # separate required vs preferred
            required  = [k for k in missing if k.get("importance") == "required"]
            preferred = [k for k in missing if k.get("importance") != "required"]

            for group_label, group in [("Required", required), ("Preferred", preferred)]:
                if not group:
                    continue
                st.markdown(f"**{group_label}**")
                rows = []
                for item in group:
                    rows.append(
                        {
                            "Keyword":    item.get("keyword", ""),
                            "Category":   _category_badge(item.get("category", "")),
                            "Importance": _importance_badge(item.get("importance", "")),
                            "Add to":     item.get("suggested_section", ""),
                            "Why it matters": item.get("why_it_matters", ""),
                        }
                    )
                df = pd.DataFrame(rows)
                st.markdown(
                    df.to_html(escape=False, index=False),
                    unsafe_allow_html=True,
                )
                st.markdown("<br>", unsafe_allow_html=True)

def render_bullet_analysis(data: dict) -> None:
    """
    Render bullet quality analysis for resume bullets.
    """

    bullets: list[dict] = data.get("bullets", [])
    score: int = int(data.get("bullet_quality_avg", 0))

    # Overall score
    if score >= ATS_PASS_THRESHOLD:
        st.success(f"Bullet Quality Score: {score} (STRONG)")
    else:
        st.error(f"Bullet Quality Score: {score} (WEAK)")

    if not bullets:
        st.info("No bullet analysis available.")
        return

    # Group bullets by quality level
    best = [b for b in bullets if b.get("level") == "L3_BEST"]
    better = [b for b in bullets if b.get("level") == "L2_BETTER"]
    ok = [b for b in bullets if b.get("level") == "L1_OK"]

    tab_best, tab_better, tab_ok = st.tabs(
        [
            f"Best ({len(best)})",
            f"Better ({len(better)})",
            f"Needs Work ({len(ok)})",
        ]
    )

    def _render_table(items: list[dict]) -> None:
        if not items:
            st.info("No bullets in this category.")
            return

        rows = []

        for item in items:
            rows.append(
                {
                    "Section": item.get("source", ""),
                    "Parent": item.get("parent_title", ""),
                    "Bullet": item.get("bullet_text", ""),
                    "Action Verb": _bool_badge(
                        item.get("has_action_verb", False)
                    ),
                    "Technology": _bool_badge(
                        item.get("has_specific_technology", False)
                    ),
                    "Impact": _bool_badge(
                        item.get("has_measurable_impact", False)
                    ),
                    "Level": _level_badge(item.get("level", "")),
                    "Missing": item.get("what_is_missing", ""),
                }
            )

        df = pd.DataFrame(rows)
        st.table(df)

    # BEST bullets
    with tab_best:
        st.text("These bullets are strong and well-structured.")
        _render_table(best)

    # BETTER bullets
    with tab_better:
        st.text("These bullets are decent but could be improved.")
        _render_table(better)

    # NEEDS WORK bullets
    with tab_ok:
        st.text("These bullets need stronger impact and specificity.")
        _render_table(ok)


def render_jargon_analysis(data: dict) -> None:
    """
    Render jargon analysis results.
    """

    flags: list[dict] = data.get("flags", [])
    score: int = int(data.get("jargon_score", 0))

    # Overall score status
    if score >= ATS_PASS_THRESHOLD:
        st.success(f"Jargon Score: {score} (GOOD)")
    else:
        st.error(f"Jargon Score: {score} (NEEDS IMPROVEMENT)")

    # No issues found
    if not flags:
        st.success("No jargon issues detected.")
        return

    # Group by severity
    grouped = {
        "high": [],
        "medium": [],
        "low": [],
    }

    for item in flags:
        severity = (item.get("severity", "low") or "low").lower()
        grouped.setdefault(severity, []).append(item)

    # Render each severity section    
    def _render_table(severity : str, items: list) -> None:
        if not items:
            return

        rows = []

        for item in items:
            rows.append(
                {
                    "Bullet": item.get("bullet_text", ""),
                    "Problematic Term": item.get("term_used", ""),
                    "Suggested Translation": item.get(
                        "suggested_translation", ""
                    ),
                    "Severity": item.get("severity", ""),
                }
            )

        df = pd.DataFrame(rows)
        st.table(df)

    tab_high, tab_med, tab_low = st.tabs(
        [
            f"High Severity ({len(grouped.get("high", []))})",
            f"Medium Severity ({len(grouped.get("medium", []))})",
            f"Low Severity ({len(grouped.get("low", []))})",
        ]
    )

    with tab_high:
        _render_table("high", items = grouped.get("high", []))
    with tab_med:
        _render_table("medium", items = grouped.get("medium", []))
    with tab_low:
        _render_table("low", items = grouped.get("low", []))
        

def render_structure_analysis(structure: dict) -> None:
    """
    Render a resume structure analysis dict in a readable Streamlit layout.
    """

    # Overall score status
    reasoning = structure.get("_reasoning") or {}
    if reasoning:
        st.subheader("Reasoning & Score")
        score = reasoning.get("structure_score") or reasoning.get("clamped_score")
        if score is not None:
            if score >= ATS_PASS_THRESHOLD:
                st.success(f"Structure Score: {score} (GOOD)")
            else:
                st.error(f"Structure Score: {score} (NEEDS IMPROVEMENT)")

    col1, col2 = st.columns(2)
    col1.metric("Estimated Pages", structure.get("page_count_estimate", "—"))
    col2.metric(
        "Single Column Layout",
        "Yes" if structure.get("single_column_likely") else "No",
    )

    # Section Headings 
    st.subheader("Section Headings")
    col_present, col_missing = st.columns(2)

    with col_present:
        st.markdown("**Present**")
        present = structure.get("section_headings_present") or []
        if present:
            for heading in present:
                st.write(f"✅ {heading}")
        else:
            st.write("_None found_")

    with col_missing:
        st.markdown("**Missing**")
        missing = structure.get("section_headings_missing") or []
        if missing:
            for heading in missing:
                st.write(f"❌ {heading}")
        else:
            st.write("_None_")

    # Three-Thirds Layout Check 
    st.subheader("Three-Thirds Layout Check")
    thirds = structure.get("three_thirds") or {}
    thirds_labels = {
        "top_third_has_name": "Top third has name",
        "top_third_has_contact": "Top third has contact info",
        "top_third_has_summary_or_featured": "Top third has summary / featured section",
        "middle_third_has_projects_or_experience": "Middle third has projects / experience",
        "bottom_third_has_skills_keywords": "Bottom third has skills / keywords",
    }
    thirds_rows = [
        {"Check": label, "Result": "✅ Yes" if thirds.get(key) else "❌ No"}
        for key, label in thirds_labels.items()
    ]
    st.table(thirds_rows)

    # ATS Red Flags 
    st.subheader("ATS Red Flags")
    flags = structure.get("ats_red_flags") or []
    if flags:
        for flag in flags:
            issue = flag.get("issue", "Unknown issue")
            evidence = flag.get("evidence", "")
            st.warning(f"**{issue}**" + (f"\n\n_{evidence}_" if evidence else ""))
    else:
        st.success("No ATS red flags detected.")

def render_degree_analysis(degree_alignment: dict) -> None:
    """
    Renders the degree alignment analysis result.
    """

    score = degree_alignment.get('degree_alignment_score', 'N/A')
    if score >= ATS_PASS_THRESHOLD:
        st.success(f"Degree Alignment Score: {score} (GOOD)")
    else:
        st.error(f"Degree Alignment Score: {score} (NEEDS IMPROVEMENT)")
        
    # Summary table
    st.table(
        {
            "Field": [
                "Student Degree",
                "Job Title (from JD)",
                "On Suggested List",
                "Matched Against",
            ],
            "Value": [
                degree_alignment.get("student_degree", "N/A"),
                degree_alignment.get("jd_title", "N/A"),
                "Yes" if degree_alignment.get("title_on_suggested_list") else "No",
                degree_alignment.get("matched_against", "N/A"),
            ],
        }
    )

    # Commentary as a separate labelled section
    st.markdown("**Fit Commentary**")
    st.write(degree_alignment.get("fit_commentary", "No commentary provided."))