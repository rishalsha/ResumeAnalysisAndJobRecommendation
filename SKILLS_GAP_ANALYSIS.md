# Skills Gap Analysis Feature - Implementation Guide

## Overview

The Skills Gap Analysis feature provides comprehensive analysis comparing a user's current skills against industry-standard requirements for their target role. It generates personalized recommendations with learning resources and roadmaps.

## Architecture

### Backend Components

#### 1. Skills Extraction (`extract_detailed_skills`)

- **Location**: `backend/llm_analyzer.py`
- **Purpose**: Extracts ALL skills from resume with detailed categorization
- **Output Categories**:
  - Programming languages (with proficiency & years of experience)
  - Frameworks
  - Tools
  - Databases
  - Platforms
  - Methodologies
  - Soft skills
  - Domain knowledge
  - Certifications

#### 2. Industry Skills Comparison (`get_industry_skills`)

- **Location**: `backend/llm_analyzer.py`
- **Purpose**: Fetches industry-standard required skills for target role
- **Parameters**:
  - `target_role`: Job title (e.g., "Backend Developer")
  - `experience_level`: "junior", "mid", or "senior"
- **Output**:
  - Must-have skills (critical for the role)
  - Nice-to-have skills (beneficial but not essential)
  - Emerging skills (growing in adoption)

#### 3. Gap Analysis (`analyze_skills_gap`)

- **Location**: `backend/llm_analyzer.py`
- **Purpose**: Comprehensive comparison and recommendation generation
- **Features**:
  - Automatic role inference if not specified
  - Caching for performance
  - Detailed gap identification
  - Priority-based recommendations
  - Learning resource suggestions
  - Skill roadmap generation

### Database Schema

#### `skills_gap_analysis` Table

```sql
CREATE TABLE skills_gap_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    target_role TEXT NOT NULL,
    experience_level TEXT DEFAULT 'mid',
    extracted_skills TEXT,                 -- JSON
    industry_skills TEXT,                  -- JSON
    missing_critical_skills TEXT,          -- JSON
    missing_nice_to_have TEXT,            -- JSON
    skill_recommendations TEXT,            -- JSON
    readiness_score INTEGER,
    analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
```

### Frontend Components

#### Skills Gap Page (`frontend/skills_gap.py`)

- **Route**: "Skills Gap Analysis" in navigation
- **Features**:
  1. Configuration section (target role, experience level)
  2. Readiness score and key metrics
  3. Interactive visualizations (Plotly charts)
  4. Present skills display (grouped by category)
  5. Missing critical skills with priorities
  6. Personalized recommendations with resources
  7. Learning roadmap (immediate/short-term/long-term)
  8. Download full analysis as JSON

## Usage Flow

### 1. User Initiates Analysis

```python
# User provides (optional):
- target_role: "Backend Developer"
- experience_level: "mid"

# System extracts resume text
# Calls analyzer.analyze_skills_gap()
```

### 2. Skills Extraction Phase

```python
# Extract detailed skills from resume
extracted_skills = analyzer.extract_detailed_skills(resume_text)

# Returns structured data:
{
    "programming_languages": [...],
    "frameworks": [...],
    "tools": [...],
    # ... other categories
}
```

### 3. Industry Comparison Phase

```python
# Get industry requirements
industry_skills = analyzer.get_industry_skills(target_role, experience_level)

# Returns:
{
    "must_have_skills": [...],
    "nice_to_have_skills": [...],
    "emerging_skills": [...]
}
```

### 4. Gap Analysis & Recommendations

```python
# Perform comprehensive analysis
gap_analysis = {
    "summary": {
        "readiness_score": 75,
        "total_skills_found": 32,
        "matching_must_have": 15,
        "missing_critical": 3
    },
    "present_skills": [...],
    "missing_critical_skills": [...],
    "skill_recommendations": [
        {
            "skill": "Kubernetes",
            "priority": "high",
            "why_learn": "Industry standard for orchestration",
            "estimated_learning_time": "4-8 weeks",
            "learning_path": [...],
            "resources": [...]
        }
    ],
    "learning_roadmap": {
        "immediate_focus": ["Docker", "CI/CD"],
        "short_term": ["Kubernetes", "AWS"],
        "long_term": ["Microservices", "Service Mesh"]
    }
}
```

### 5. Visualization & Display

- Interactive charts using Plotly
- Filterable recommendations
- Expandable skill details
- Download options

## API Usage

### Analyze Skills Gap

```python
from backend.llm_analyzer import LLMAnalyzer

analyzer = LLMAnalyzer()

# Full analysis
result = analyzer.analyze_skills_gap(
    resume_text="<resume content>",
    target_role="Backend Developer",  # Optional (auto-inferred if None)
    experience_level="mid"
)

# Check for errors
if "error" in result:
    print(f"Error: {result['error']}")
else:
    print(f"Readiness Score: {result['summary']['readiness_score']}%")
    print(f"Missing Critical: {len(result['missing_critical_skills'])}")
```

### Save to Database

```python
from utils.database import save_skills_gap_analysis

analysis_id = save_skills_gap_analysis(
    user_id=user_id,
    target_role=result["target_role"],
    experience_level=result["experience_level"],
    gap_analysis_data=result
)
```

### Retrieve from Database

```python
from utils.database import get_skills_gap_analysis

# Get latest analysis
analysis = get_skills_gap_analysis(user_id, limit=1)

# Get history (last 5)
history = get_skills_gap_analysis(user_id, limit=5)
```

## Customization

### Adding New Skill Categories

1. Update `extract_detailed_skills` prompt in `llm_analyzer.py`
2. Add category to JSON structure
3. Update frontend display in `skills_gap.py`

### Modifying Learning Resources

Learning resources are generated by LLM based on:

- Current industry trends
- Skill difficulty level
- User's experience level
- Prerequisite requirements

To customize resource types, modify the prompt in `analyze_skills_gap` function.

### Adjusting Visualization

Charts are created using Plotly. Customize in `display_skills_gap_results`:

```python
# Example: Change chart type
fig = px.pie(...)  # Change to px.bar(...) for bar chart
st.plotly_chart(fig, use_container_width=True)
```

## Performance Considerations

### Caching

- Skills extraction is cached by resume content hash
- Gap analysis is cached by role + experience level
- Cache location: `logs/.cache/`

### Clear Cache

Users can clear cache via Settings → Advanced Cache Options

### Analysis Time

- Typical duration: 2-3 minutes
- Stages:
  1. Skills extraction: ~30-45 seconds
  2. Industry comparison: ~20-30 seconds
  3. Gap analysis: ~60-90 seconds

## Error Handling

Common errors and solutions:

1. **No resume uploaded**

   - Check: `user['resume_file_path']`
   - Solution: Redirect to Profile page

2. **Ollama connection failed**

   - Check: Ollama service running
   - Solution: Display connection test results

3. **JSON parsing errors**

   - Cause: LLM returns invalid JSON
   - Solution: Retry with enhanced prompt

4. **Timeout errors**
   - Increase: `REQUEST_TIMEOUT` in `.env`
   - Current: 180 seconds

## Future Enhancements

### Planned Features

1. **Skill Progress Tracking**: Track skill acquisition over time
2. **Learning Resource Integration**: Direct links to courses
3. **Skill Assessment Tests**: Verify claimed proficiency
4. **Peer Comparison**: Anonymous benchmark against peers
5. **Job Market Trends**: Real-time demand analysis
6. **Customizable Templates**: Industry-specific skill templates

### Advanced Analytics

- Skill decay analysis (outdated skills)
- Career path predictions
- Salary impact estimates
- Certification ROI analysis

## Testing

### Unit Tests

```python
# Test skills extraction
def test_extract_detailed_skills():
    analyzer = LLMAnalyzer()
    result = analyzer.extract_detailed_skills(sample_resume)
    assert "programming_languages" in result
    assert len(result["programming_languages"]) > 0

# Test gap analysis
def test_analyze_skills_gap():
    analyzer = LLMAnalyzer()
    result = analyzer.analyze_skills_gap(
        sample_resume,
        "Backend Developer",
        "mid"
    )
    assert "summary" in result
    assert "readiness_score" in result["summary"]
```

### Integration Tests

1. Upload resume
2. Run skills gap analysis
3. Verify database save
4. Check visualization rendering
5. Test download functionality

## Troubleshooting

### Issue: Low skill count

- **Cause**: Prompt not comprehensive enough
- **Solution**: Enhanced prompt to request 20-50+ skills

### Issue: Inaccurate proficiency levels

- **Cause**: Years of experience not clearly stated
- **Solution**: LLM estimates from context (projects, roles)

### Issue: Missing recommendations

- **Cause**: No clear gaps or perfect match
- **Solution**: Always provide emerging/trendin skills

## Contributing

To extend this feature:

1. Review existing prompt templates
2. Test with diverse resume samples
3. Validate JSON structure
4. Update documentation
5. Add error handling
6. Create unit tests

## Dependencies

- **Python**: 3.8+
- **Streamlit**: 1.52.0
- **Plotly**: 5.18.0
- **Ollama**: >= 0.0.50
- **LLM Model**: llama3.2:3b or ministral-3:3b

## License

Part of Resume Analysis and Job Recommendation System.
