import streamlit as st
import json

from backend.auth import is_user_logged_in, get_current_user_name
from backend.llm_analyzer import LLMAnalyzer
from utils.database import get_db_connection, save_resume_analysis, get_user_analysis


def _get_user_resume_text_with_ts():
    """Fetch the user's most recent extracted resume text and its timestamp."""
    user_id = st.session_state.get("user_id")
    if not user_id:
        return "", None

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT extracted_text, analysis_timestamp
            FROM resume_analysis
            WHERE user_id = ?
            ORDER BY analysis_timestamp DESC
            LIMIT 1
            """,
            (user_id,),
        )
        row = cursor.fetchone()
        if not row:
            return "", None
        return row["extracted_text"], row["analysis_timestamp"]
    finally:
        conn.close()


def _display_strengths(strengths_data):
    """Display strengths with visual formatting."""
    if isinstance(strengths_data, dict):
        if "strengths" in strengths_data:
            strengths = strengths_data["strengths"]
            summary = strengths_data.get("summary", "")
            
            if summary:
                st.info(f"📋 **Summary:** {summary}")
            
            if isinstance(strengths, list):
                for i, item in enumerate(strengths, 1):
                    if isinstance(item, dict):
                        strength = item.get("strength", str(item))
                        category = item.get("category", "general")
                        importance = item.get("importance", "medium")
                        confidence = item.get("confidence", 0)
                        examples = item.get("examples", [])
                        
                        # Color code by importance
                        if importance == "critical":
                            color = "🔴"
                        elif importance == "high":
                            color = "🟠"
                        else:
                            color = "🟡"
                        
                        with st.container():
                            st.markdown(f"{color} **{i}. {strength}**")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.caption(f"📌 Category: `{category}`")
                            with col2:
                                st.caption(f"⭐ Importance: `{importance}`")
                            with col3:
                                st.caption(f"🎯 Confidence: `{confidence}%`")
                            
                            if examples:
                                st.markdown("**Examples from resume:**")
                                for ex in examples:
                                    st.markdown(f"- _{ex}_")
                            st.divider()
                    else:
                        st.markdown(f"• {item}")


def _display_weaknesses(weaknesses_data):
    """Display weaknesses with visual formatting and severity levels."""
    if isinstance(weaknesses_data, dict):
        if "weaknesses" in weaknesses_data:
            weaknesses = weaknesses_data["weaknesses"]
            assessment = weaknesses_data.get("overall_assessment", "")
            
            if assessment:
                st.warning(f"📋 **Overall Assessment:** {assessment}")
            
            if isinstance(weaknesses, list):
                for i, item in enumerate(weaknesses, 1):
                    if isinstance(item, dict):
                        weakness = item.get("weakness", str(item))
                        category = item.get("category", "general")
                        severity = item.get("severity", "minor")
                        confidence = item.get("confidence", 0)
                        location = item.get("location", "unknown")
                        impact = item.get("impact", "")
                        fix = item.get("fix", "")
                        examples = item.get("examples", [])
                        
                        # Color code by severity
                        if severity == "critical":
                            color = "🔴"
                            severity_style = "**CRITICAL**"
                        elif severity == "moderate":
                            color = "🟠"
                            severity_style = "**MODERATE**"
                        else:
                            color = "🟡"
                            severity_style = "**MINOR**"
                        
                        with st.container():
                            st.markdown(f"{color} **{i}. {weakness}**")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.caption(f"📌 Category: `{category}`")
                            with col2:
                                st.caption(f"⚠️ Severity: `{severity_style}`")
                            with col3:
                                st.caption(f"🎯 Confidence: `{confidence}%`")
                            
                            st.markdown(f"📍 **Location:** {location}")
                            
                            if impact:
                                st.markdown(f"💥 **Impact:** {impact}")
                            
                            if fix:
                                st.markdown(f"✅ **How to fix:** {fix}")
                            
                            if examples:
                                st.markdown("**Examples from resume:**")
                                for ex in examples:
                                    st.markdown(f"- _{ex}_")
                            
                            st.divider()
                    else:
                        st.markdown(f"• {item}")


def analysis_page():
    if not is_user_logged_in():
        st.error("You need to be logged in to access this page.")
        st.stop()

    st.title("🔍 AI Resume Analysis")
    st.caption("Analyze your uploaded resume using AI-powered insights")

    # Fetch user's resume from database - always fresh (with timestamp)
    resume_text, resume_ts = _get_user_resume_text_with_ts()
    
    if not resume_text:
        st.warning("❌ No resume found. Please upload a resume in the Dashboard first.")
        if st.button("Go to Dashboard to Upload"):
            st.session_state['page'] = 'Dashboard'
            st.rerun()
        st.stop()

    st.success("✅ Resume loaded and ready for analysis")

    # Refresh editable text if database content changed
    if (
        "resume_source_ts" not in st.session_state
        or st.session_state.get("resume_source_ts") != resume_ts
    ):
        st.session_state["resume_text"] = resume_text
        st.session_state["resume_source_ts"] = resume_ts

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📄 Your Resume")
        st.session_state["resume_text"] = st.text_area(
            "Resume text (editable)",
            value=st.session_state.get("resume_text", ""),
            height=300,
        )

    with col2:
        st.subheader("⚙️ Analysis Settings")
        # All analyses run comprehensively; no per-type selection
        with st.expander("Advanced Options", expanded=False):
            st.caption("💡 Using Ollama for local AI processing")
            st.caption("✨ Results are cached to save processing time")
            cache_enabled = st.checkbox("Enable result caching", value=True)

    run = st.button("🚀 Run Analysis", type="primary", use_container_width=True)

    if run:
        resume_text = st.session_state.get("resume_text", "").strip()
        if not resume_text:
            st.warning("Please provide resume text.")
            st.stop()

        analyzer = LLMAnalyzer()

        with st.spinner("🤖 Analyzing your resume..."):
            conn = analyzer.test_connection()
            if conn.get("status") == "error":
                st.error(f"❌ {conn.get('message', 'Connection failed.')}")
                st.stop()

            try:
                # Always use comprehensive analysis to get all data at once
                result = analyzer.comprehensive_analysis(resume_text, use_cache=cache_enabled)
            except Exception as e:
                st.error(f"❌ Analysis failed: {e}")
                return

        # Check for errors
        if "error" in result:
            st.error(f"❌ {result['error']}")
            if result.get("raw_response"):
                with st.expander("LLM raw response"):
                    st.code(result["raw_response"], language="json")
            st.stop()

        # Display results
        st.subheader("📊 Comprehensive Analysis Results")
        
        # Show cache status
        if result.get("cached"):
            st.info("⚡ **Cached Result** - Retrieved from cache (faster)")
        
        # Overall score
        overall_score = result.get("overall_score")
        if isinstance(overall_score, int):
            st.metric("Overall Resume Score", f"{overall_score}/100")

        # Create tabs for different analysis types
        tabs = st.tabs(["🌟 Strengths", "⚠️ Weaknesses", "🔧 Skills", "💡 Suggestions"])
        
        # TAB 1: STRENGTHS
        with tabs[0]:
            strengths_data = result.get("strengths", {})
            summary = strengths_data.get("summary")
            if summary:
                st.info(f"Summary: {summary}")

            items = strengths_data.get("items", [])
            if items:
                st.markdown(f"**{len(items)} strengths found:**")
                for item in items:
                    strength = item.get("strength", "N/A")
                    meta = []
                    if item.get("category"):
                        meta.append(f"Category: {item['category']}")
                    if item.get("importance"):
                        meta.append(f"Importance: {item['importance']}")
                    if item.get("confidence") is not None:
                        meta.append(f"Confidence: {item['confidence']}%")
                    line = f"- **{strength}**"
                    if meta:
                        line += " (" + " | ".join(meta) + ")"
                    st.markdown(line)
                    examples = item.get("examples", [])
                    if examples:
                        st.caption("Examples:")
                        for ex in examples[:2]:
                            st.markdown(f"  • {ex}")
            else:
                st.info("No strengths identified yet.")
        
        # TAB 2: WEAKNESSES
        with tabs[1]:
            weaknesses_data = result.get("weaknesses", {})
            summary = weaknesses_data.get("summary")
            if summary:
                st.warning(f"Summary: {summary}")

            items = weaknesses_data.get("items", [])
            if items:
                st.markdown(f"**{len(items)} areas to improve:**")
                for item in items:
                    weakness = item.get("weakness", "N/A")
                    severity = item.get("severity", "minor")
                    meta = []
                    if item.get("category"):
                        meta.append(f"Category: {item['category']}")
                    if severity:
                        meta.append(f"Severity: {severity}")
                    if item.get("confidence") is not None:
                        meta.append(f"Confidence: {item['confidence']}%")
                    line = f"- **{weakness}**"
                    if meta:
                        line += " (" + " | ".join(meta) + ")"
                    st.markdown(line)

                    details = []
                    if item.get("location"):
                        details.append(f"Location: {item['location']}")
                    if item.get("impact"):
                        details.append(f"Impact: {item['impact']}")
                    if item.get("fix"):
                        details.append(f"Fix: {item['fix']}")
                    for detail in details:
                        st.caption(detail)

                    examples = item.get("examples", [])
                    if examples:
                        st.caption("Examples:")
                        for ex in examples[:2]:
                            st.markdown(f"  • {ex}")
            else:
                st.info("No weaknesses identified yet.")
        
        # TAB 3: SKILLS
        with tabs[2]:
            skills_data = result.get("skills", {})
            summary = skills_data.get("summary")
            if summary:
                st.info(f"Summary: {summary}")

            st.subheader("🔧 Technical Skills")
            technical = skills_data.get("technical", [])
            if technical:
                for skill in technical:
                    if isinstance(skill, dict):
                        name = skill.get("skill", "N/A")
                        proficiency = skill.get("proficiency", "intermediate")
                        st.markdown(f"- **{name}** ({proficiency})")
                    else:
                        st.markdown(f"- {skill}")
            else:
                st.info("No technical skills identified.")

            st.subheader("💼 Soft Skills")
            soft = skills_data.get("soft_skills", [])
            if soft:
                for skill in soft:
                    if isinstance(skill, dict):
                        name = skill.get("skill", "N/A")
                        proficiency = skill.get("proficiency", "intermediate")
                        st.markdown(f"- **{name}** ({proficiency})")
                    else:
                        st.markdown(f"- {skill}")
            else:
                st.info("No soft skills identified.")
        
        # TAB 4: SUGGESTIONS
        with tabs[3]:
            suggestions_data = result.get("suggestions", {})
            summary = suggestions_data.get("summary")
            if summary:
                st.info(f"Roadmap: {summary}")

            improvements = suggestions_data.get("priority_improvements", [])
            if improvements:
                st.markdown(f"**{len(improvements)} priority items:**")
                for imp in improvements:
                    title = imp.get("improvement", "N/A")
                    meta = []
                    if imp.get("priority"):
                        meta.append(f"Priority: {imp['priority']}")
                    if imp.get("impact"):
                        meta.append(f"Impact: {imp['impact']}")
                    if imp.get("timeline"):
                        meta.append(f"Timeline: {imp['timeline']}")
                    line = f"- **{title}**"
                    if meta:
                        line += " (" + " | ".join(meta) + ")"
                    st.markdown(line)
            else:
                st.info("No suggestions available yet.")

        # Compute summary scores for analysis
        def _compute_scores(res):
            scores = {
                "strengths": {"count": 0, "avg_confidence": 0, "critical": 0, "high": 0, "medium": 0},
                "weaknesses": {"count": 0, "avg_confidence": 0, "critical": 0, "moderate": 0, "minor": 0},
                "skills": {"technical_count": 0, "soft_count": 0},
            }
            s_items = res.get("strengths", {}).get("items", [])
            w_items = res.get("weaknesses", {}).get("items", [])
            tech = res.get("skills", {}).get("technical", [])
            soft = res.get("skills", {}).get("soft_skills", [])

            if s_items:
                scores["strengths"]["count"] = len(s_items)
                confidences = [x.get("confidence", 0) for x in s_items if isinstance(x, dict)]
                scores["strengths"]["avg_confidence"] = int(sum(confidences) / max(len(confidences), 1))
                for x in s_items:
                    imp = str(x.get("importance", "medium")).lower()
                    if imp in scores["strengths"]:
                        scores["strengths"][imp] += 1

            if w_items:
                scores["weaknesses"]["count"] = len(w_items)
                confidences = [x.get("confidence", 0) for x in w_items if isinstance(x, dict)]
                scores["weaknesses"]["avg_confidence"] = int(sum(confidences) / max(len(confidences), 1))
                for x in w_items:
                    sev = str(x.get("severity", "minor")).lower()
                    if sev in scores["weaknesses"]:
                        scores["weaknesses"][sev] += 1

            scores["skills"]["technical_count"] = len(tech) if isinstance(tech, list) else 0
            scores["skills"]["soft_count"] = len(soft) if isinstance(soft, list) else 0
            return scores

        # Persist single overall score only
        scores = overall_score if isinstance(overall_score, int) else None

        # SAVE ALL DATA TO DATABASE
        user_id = st.session_state.get("user_id")
        if user_id:
            try:
                # Save comprehensive data as JSON strings
                save_resume_analysis(
                    user_id=user_id,
                    extracted_text=resume_text,
                    strengths=result.get("strengths", {}),
                    weaknesses=result.get("weaknesses", {}),
                    skills=result.get("skills", {}),
                    suggestions=result.get("suggestions", {}),
                    analysis_scores=scores,
                )
                st.success("✅ Complete analysis saved to your profile")
            except Exception as e:
                st.warning(f"⚠️ Analysis complete but could not save: {e}")

        # Show token stats
        stats = analyzer.get_token_stats()
        with st.expander("📈 Token Statistics"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Tokens", stats.get('total_tokens', 0))
            with col2:
                st.metric("API Requests", stats.get('requests_count', 0))
            with col3:
                if stats.get('requests_count', 0) > 0:
                    avg_tokens = stats.get('total_tokens', 0) // stats.get('requests_count', 1)
                    st.metric("Avg Tokens/Request", avg_tokens)

