import streamlit as st
import json
from backend.auth import is_user_logged_in, get_logged_in_user_id
from backend.llm_analyzer import LLMAnalyzer
from utils.database import get_user_by_email, save_skills_gap_analysis, get_skills_gap_analysis, get_db_connection
import plotly.graph_objects as go
import plotly.express as px

def skills_gap_page():
    """Skills Gap Analysis Page - Comprehensive skills analysis with recommendations."""
    
    if not is_user_logged_in():
        st.error("You need to be logged in to access this page.")
        st.stop()
    
    user_id = get_logged_in_user_id()
    
    st.title("🎯 Skills Gap Analysis")
    st.markdown("""
    Discover which skills you have, which ones you need, and get a personalized learning roadmap 
    to advance your career.
    """)
    
    # Check if resume has been analyzed (extracted text exists in database)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT extracted_text FROM resume_analysis WHERE user_id = ? LIMIT 1", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row or not row[0]:
        st.warning("⚠️ Please upload and analyze your resume in the Resume Analysis page first.")
        return
    
    # Configuration section
    st.header("📋 Analysis Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        target_role = st.text_input(
            "Target Job Role",
            placeholder="e.g., Backend Developer, Data Scientist",
            help="Leave empty to auto-detect from your resume"
        )
    
    with col2:
        experience_level = st.selectbox(
            "Experience Level",
            ["junior", "mid", "senior"],
            index=1,
            help="Your current or target experience level"
        )
    
    # Analyze button
    if st.button("🔍 Analyze Skills Gap", type="primary", use_container_width=True):
        with st.spinner("Analyzing your skills and comparing with industry standards... This may take 2-3 minutes."):
            try:
                # Get resume text and identified skills from database
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT extracted_text, identified_skills 
                    FROM resume_analysis 
                    WHERE user_id = ? 
                    ORDER BY analysis_timestamp DESC 
                    LIMIT 1
                """, (user_id,))
                row = cursor.fetchone()
                conn.close()
                
                if not row or not row[0]:
                    st.error("No resume text found. Please upload and analyze your resume first in the Resume Analysis page.")
                    return
                
                resume_text = row[0]
                identified_skills = json.loads(row[1]) if row[1] else None
                
                if not identified_skills:
                    st.error("No skills found in database. Please run Resume Analysis first to extract skills.")
                    return
                
                # Initialize analyzer
                analyzer = LLMAnalyzer()
                
                # Perform skills gap analysis using pre-extracted skills
                gap_analysis = analyzer.analyze_skills_gap_from_extracted(
                    extracted_skills=identified_skills,
                    target_role=target_role if target_role else None,
                    experience_level=experience_level
                )
                
                if "error" in gap_analysis:
                    st.error(f"Analysis failed: {gap_analysis['error']}")
                    return
                
                # Save to database
                save_skills_gap_analysis(
                    user_id,
                    gap_analysis.get("target_role", target_role or "Unknown"),
                    experience_level,
                    gap_analysis
                )
                
                # Store in session state for display
                st.session_state['skills_gap_analysis'] = gap_analysis
                st.success("✅ Analysis complete!")
                st.rerun()
                
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                return
    
    st.divider()
    
    # Display results
    # Check for analysis in session state or database
    gap_analysis = st.session_state.get('skills_gap_analysis')
    
    if not gap_analysis:
        # Try to load from database
        db_analysis = get_skills_gap_analysis(user_id)
        if db_analysis:
            gap_analysis = db_analysis
            st.session_state['skills_gap_analysis'] = gap_analysis
    
    if not gap_analysis:
        st.info("👆 Click 'Analyze Skills Gap' to get started with your personalized skills analysis.")
        return
    
    # Debug: Show what data we have
    with st.expander("🔍 Debug: View Raw Analysis Data", expanded=False):
        st.json(gap_analysis)
    
    # Display Analysis Results
    display_skills_gap_results(gap_analysis)


def display_skills_gap_results(analysis):
    """Display comprehensive skills gap analysis results with visualizations."""
    
    # Check if analysis has error
    if "error" in analysis:
        st.error(f"Analysis Error: {analysis['error']}")
        if "raw_response" in analysis:
            with st.expander("View Raw Response"):
                st.text(analysis["raw_response"])
        return
    
    summary = analysis.get("summary", {})
    target_role = analysis.get("target_role", "Unknown")
    experience_level = analysis.get("experience_level", "mid")
    
    # Show warning if summary is empty
    if not summary:
        st.warning("⚠️ Analysis completed but summary data is missing. The LLM may not have returned data in the expected format.")
    
    # Summary Section
    st.header(f"📊 Analysis for: {target_role} ({experience_level.title()} Level)")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Readiness Score",
            f"{summary.get('readiness_score', 0)}%",
            delta=None
        )
    
    with col2:
        st.metric(
            "Total Skills",
            summary.get('total_skills_found', 0)
        )
    
    with col3:
        st.metric(
            "Must-Have Match",
            f"{summary.get('matching_must_have', 0)}"
        )
    
    with col4:
        st.metric(
            "Critical Gaps",
            summary.get('missing_critical', 0),
            delta=f"-{summary.get('missing_critical', 0)}",
            delta_color="inverse"
        )
    
    # Strength and Gap Areas
    col1, col2 = st.columns(2)
    
    with col1:
        st.success("**💪 Strength Areas:**")
        for area in summary.get('strength_areas', []):
            st.write(f"- {area}")
    
    with col2:
        st.warning("**🎯 Gap Areas:**")
        for area in summary.get('gap_areas', []):
            st.write(f"- {area}")
    
    st.divider()
    
    # Visualizations
    st.header("📈 Skills Visualization")
    
    viz_data = analysis.get("visualization_data", {})
    
    # Create tabs for different visualizations
    tab1, tab2, tab3 = st.tabs(["Skills by Category", "Proficiency Distribution", "Gap Severity"])
    
    with tab1:
        if viz_data.get("skills_by_category"):
            fig = px.bar(
                x=list(viz_data["skills_by_category"].keys()),
                y=list(viz_data["skills_by_category"].values()),
                labels={"x": "Category", "y": "Number of Skills"},
                title="Skills Distribution by Category"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        if viz_data.get("proficiency_distribution"):
            fig = px.pie(
                names=list(viz_data["proficiency_distribution"].keys()),
                values=list(viz_data["proficiency_distribution"].values()),
                title="Proficiency Level Distribution"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        if viz_data.get("gap_severity"):
            fig = px.bar(
                x=list(viz_data["gap_severity"].keys()),
                y=list(viz_data["gap_severity"].values()),
                labels={"x": "Severity", "y": "Number of Gaps"},
                title="Skills Gap Severity",
                color=list(viz_data["gap_severity"].keys()),
                color_discrete_map={"critical": "red", "moderate": "orange", "minor": "yellow"}
            )
            st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # Present Skills
    st.header("✅ Your Current Skills")
    present_skills = analysis.get("present_skills", [])
    
    if present_skills:
        # Group by category
        skills_by_category = {}
        for skill in present_skills:
            category = skill.get("category", "other")
            if category not in skills_by_category:
                skills_by_category[category] = []
            skills_by_category[category].append(skill)
        
        for category, skills in skills_by_category.items():
            with st.expander(f"**{category.replace('_', ' ').title()}** ({len(skills)} skills)", expanded=False):
                for skill in skills:
                    col1, col2, col3 = st.columns([3, 2, 1])
                    with col1:
                        st.write(f"**{skill['skill']}**")
                    with col2:
                        st.write(f"Proficiency: {skill.get('proficiency', 'N/A').title()}")
                    with col3:
                        if skill.get('matches_requirement'):
                            st.success("✓ Required")
                        else:
                            st.info("ℹ️ Bonus")
    
    st.divider()
    
    # Missing Critical Skills
    st.header("🚨 Missing Critical Skills")
    missing_critical = analysis.get("missing_critical_skills", [])
    
    if missing_critical:
        for skill in missing_critical:
            with st.expander(f"**{skill['skill']}** - {skill.get('category', '').replace('_', ' ').title()}", expanded=True):
                st.write(f"**Priority:** {skill.get('priority', 'N/A').upper()}")
                st.write(f"**Why Important:** {skill.get('why_important', 'N/A')}")
                st.write(f"**Learning Time:** {skill.get('typical_learning_time', 'N/A')}")
    else:
        st.success("🎉 You have all critical skills for this role!")
    
    st.divider()
    
    # Skill Recommendations
    st.header("🎓 Personalized Skill Recommendations")
    recommendations = analysis.get("skill_recommendations", [])
    
    if recommendations:
        # Filter by priority
        priority_filter = st.multiselect(
            "Filter by Priority",
            ["high", "medium", "low"],
            default=["high", "medium"]
        )
        
        filtered_recs = [r for r in recommendations if r.get("priority") in priority_filter]
        
        for i, rec in enumerate(filtered_recs[:10], 1):
            priority_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            
            with st.expander(
                f"{priority_color.get(rec.get('priority'), '⚪')} **{i}. {rec['skill']}** - {rec.get('category', '').replace('_', ' ').title()}",
                expanded=(i <= 3)
            ):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**Why Learn:** {rec.get('why_learn', 'N/A')}")
                    st.write(f"**Current Demand:** {rec.get('current_demand', 'N/A').title()}")
                    
                    if rec.get('prerequisites'):
                        st.write(f"**Prerequisites:** {', '.join(rec['prerequisites'])}")
                    
                    if rec.get('use_cases'):
                        st.write("**Use Cases:**")
                        for uc in rec['use_cases'][:3]:
                            st.write(f"  - {uc}")
                
                with col2:
                    st.info(f"**Difficulty:** {rec.get('difficulty', 'N/A').title()}")
                    st.info(f"**Learning Time:** {rec.get('estimated_learning_time', 'N/A')}")
                
                # Learning path
                if rec.get('learning_path'):
                    st.write("**📚 Learning Path:**")
                    for j, step in enumerate(rec['learning_path'], 1):
                        st.write(f"{j}. {step}")
                
                # Resources
                if rec.get('resources'):
                    st.write("**🔗 Learning Resources:**")
                    for resource in rec['resources']:
                        resource_type = resource.get('type', 'resource').title()
                        resource_name = resource.get('name', 'Resource')
                        resource_cost = resource.get('cost', 'unknown').title()
                        st.write(f"- **{resource_type}:** {resource_name} ({resource_cost})")
    
    st.divider()
    
    # Learning Roadmap
    st.header("🗺️ Your Learning Roadmap")
    roadmap = analysis.get("learning_roadmap", {})
    
    if roadmap:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.info("**🚀 Immediate Focus (1-2 months)**")
            for skill in roadmap.get('immediate_focus', []):
                st.write(f"- {skill}")
        
        with col2:
            st.success("**📈 Short-term (3-6 months)**")
            for skill in roadmap.get('short_term', []):
                st.write(f"- {skill}")
        
        with col3:
            st.warning("**🎯 Long-term (6-12 months)**")
            for skill in roadmap.get('long_term', []):
                st.write(f"- {skill}")
    
    # Download option
    st.divider()
    
    if st.button("📥 Download Full Analysis Report", use_container_width=True):
        # Create downloadable JSON
        report = json.dumps(analysis, indent=2)
        st.download_button(
            label="Download JSON Report",
            data=report,
            file_name=f"skills_gap_analysis_{analysis.get('target_role', 'report')}.json",
            mime="application/json"
        )
