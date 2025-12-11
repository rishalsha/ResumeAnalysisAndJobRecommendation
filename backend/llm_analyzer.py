import os
import json
import logging
import time
import requests
from typing import Dict, List, Any, Optional, Callable
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Configure logging
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

log_file = os.getenv("LOG_FILE", "logs/app.log")
log_level = getattr(logging, os.getenv("LOG_LEVEL", "INFO"))

logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TokenCounter:
    """Track token usage for cost monitoring."""
    
    def __init__(self):
        self.total_tokens = 0
        self.requests_count = 0
        self.api_calls_log = []
    
    def add_tokens(self, prompt_tokens: int, response_tokens: int, model: str):
        """Add token count from a request."""
        total = prompt_tokens + response_tokens
        self.total_tokens += total
        self.requests_count += 1
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "prompt_tokens": prompt_tokens,
            "response_tokens": response_tokens,
            "total_tokens": total
        }
        self.api_calls_log.append(log_entry)
        
        logger.info(f"Tokens used: {total} | Total so far: {self.total_tokens} | Request #{self.requests_count}")
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (approximation for Ollama)."""
        # Rough estimate: ~4 characters per token
        return len(text) // 4
    
    def get_stats(self) -> Dict[str, Any]:
        """Get token usage statistics."""
        return {
            "total_tokens": self.total_tokens,
            "requests_count": self.requests_count,
            "api_calls_log": self.api_calls_log
        }


class LLMAnalyzer:
    """
    Analyze resumes using Ollama LLM.
    Supports prompt templates for different analysis tasks.
    """
    
    def __init__(self, model: Optional[str] = None):
        """Initialize LLM Analyzer with Ollama client."""
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.model = model or os.getenv("OLLAMA_MODEL", "mistral")
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.timeout = int(os.getenv("REQUEST_TIMEOUT", "30"))
        self.temperature = float(os.getenv("TEMPERATURE", "0.2"))
        self.max_tokens = int(os.getenv("MAX_TOKENS", "1024"))
        
        self.token_counter = TokenCounter()
        self.client = None
        
        logger.info(f"Initializing LLMAnalyzer with model: {self.model}, host: {self.ollama_host}")
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Ollama client with error handling."""
        try:
            import ollama
            # Set the Ollama host from environment
            os.environ["OLLAMA_HOST"] = self.ollama_host
            self.client = ollama.Client(host=self.ollama_host)
            logger.info("Ollama client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Ollama client: {e}")
            self.client = None
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Ollama server."""
        logger.info("Testing Ollama connection...")
        
        try:
            # Try to list available models
            response = requests.get(
                f"{self.ollama_host}/api/tags",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                models = [m.get("name", "unknown") for m in data.get("models", [])]
                
                if self.model in models:
                    logger.info(f"Connection successful. Model '{self.model}' is available.")
                    return {
                        "status": "success",
                        "message": f"Ollama connected successfully. Model '{self.model}' available.",
                        "host": self.ollama_host,
                        "available_models": models
                    }
                else:
                    logger.warning(f"Model '{self.model}' not found. Available: {models}")
                    return {
                        "status": "warning",
                        "message": f"Model '{self.model}' not found. Pull it with: ollama pull {self.model}",
                        "host": self.ollama_host,
                        "available_models": models
                    }
            else:
                logger.error(f"Ollama returned status {response.status_code}")
                return {
                    "status": "error",
                    "message": f"Ollama server returned status {response.status_code}",
                    "host": self.ollama_host
                }
                
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            return {
                "status": "error",
                "message": f"Cannot connect to Ollama at {self.ollama_host}. Is it running?",
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error during connection test: {e}")
            return {
                "status": "error",
                "message": f"Unexpected error: {str(e)}",
                "error": str(e)
            }
    
    # ============ PROMPT TEMPLATES ============
    
    def get_strengths_prompt(self, resume_text: str) -> str:
        """Generate prompt for identifying resume strengths."""
        return f"""You are an expert career coach and resume analyzer. 
Analyze the following resume and identify the candidate's key strengths and achievements.

Resume:
{resume_text}

Provide your analysis as a JSON object with the following structure:
{{"strengths": ["strength1", "strength2", ...]}}

Focus on:
- Technical skills and expertise
- Professional achievements and impact
- Leadership and soft skills
- Education and certifications
- Industry experience and domain knowledge

Return ONLY valid JSON, no additional text."""
    
    def get_weaknesses_prompt(self, resume_text: str) -> str:
        """Generate prompt for identifying resume weaknesses."""
        return f"""You are an expert career coach and resume analyzer.
Analyze the following resume and identify potential weaknesses and areas for improvement.

Resume:
{resume_text}

Provide your analysis as a JSON object with the following structure:
{{"weaknesses": ["weakness1", "weakness2", ...]}}

Focus on:
- Missing critical skills for the industry
- Gaps in experience or education
- Areas lacking specific examples
- Outdated technologies or methodologies
- Communication or formatting issues

Return ONLY valid JSON, no additional text."""
    
    def get_skills_extraction_prompt(self, resume_text: str) -> str:
        """Generate prompt for extracting skills."""
        return f"""You are an expert resume analyst. Extract all technical and soft skills from the resume.

Resume:
{resume_text}

Provide your analysis as a JSON object with the following structure:
{{"technical_skills": ["skill1", "skill2", ...], "soft_skills": ["skill1", "skill2", ...]}}

Categorize skills appropriately.
Return ONLY valid JSON, no additional text."""
    
    def get_improvement_suggestions_prompt(self, resume_text: str) -> str:
        """Generate prompt for improvement suggestions."""
        return f"""You are an expert career coach and resume writer.
Provide actionable suggestions to improve the following resume.

Resume:
{resume_text}

Provide your analysis as a JSON object with the following structure:
{{"suggestions": ["suggestion1", "suggestion2", ...]}}

Focus on:
- Specific, actionable improvements
- Content and structure enhancements
- Impactful ways to present achievements
- Keywords and industry terminology
- Formatting and presentation tips

Return ONLY valid JSON, no additional text."""
    
    def get_job_match_prompt(self, resume_text: str, job_description: str) -> str:
        """Generate prompt for job matching analysis."""
        return f"""You are an expert recruiter and career matcher.
Analyze how well the candidate's resume matches the job description.

Resume:
{resume_text}

Job Description:
{job_description}

Provide your analysis as a JSON object with the following structure:
{{
    "match_score": 0-100,
    "matching_skills": ["skill1", "skill2", ...],
    "missing_skills": ["skill1", "skill2", ...],
    "strengths_for_role": ["strength1", "strength2", ...],
    "recommendations": ["recommendation1", "recommendation2", ...]
}}

Return ONLY valid JSON, no additional text."""
    
    # ============ LLM CALL METHODS ============
    
    def _call_ollama_with_retry(self, prompt: str) -> Optional[str]:
        """Call Ollama API with retry logic and error handling."""
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Calling Ollama (attempt {attempt + 1}/{self.max_retries})...")
                
                response = requests.post(
                    f"{self.ollama_host}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "temperature": self.temperature,
                        "num_predict": self.max_tokens
                    },
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info("Ollama response received successfully")
                    return data.get("response", "")
                elif response.status_code == 429:
                    logger.warning(f"Rate limited (429). Retrying in {2 ** attempt}s...")
                    time.sleep(2 ** attempt)
                else:
                    logger.error(f"Ollama returned status {response.status_code}: {response.text}")
                    if attempt < self.max_retries - 1:
                        time.sleep(2 ** attempt)
                        
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout (attempt {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Connection error (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
            except Exception as e:
                logger.error(f"Unexpected error during API call: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
        
        logger.error(f"Failed to get response from Ollama after {self.max_retries} attempts")
        return None
    
    def analyze_resume(self, resume_text: str, prompt_func: Callable) -> Dict[str, Any]:
        """
        Analyze resume using the provided prompt function.
        
        Args:
            resume_text: The resume text to analyze
            prompt_func: Function that takes resume_text and returns a prompt
        
        Returns:
            Dictionary with analysis results or error message
        """
        try:
            # Generate prompt
            prompt = prompt_func(resume_text)
            prompt_tokens = self.token_counter.estimate_tokens(prompt)
            
            # Call LLM
            response_text = self._call_ollama_with_retry(prompt)
            
            if not response_text:
                logger.error("No response from Ollama")
                return {"error": "No response from Ollama. Check connection."}
            
            # Parse response
            parsed = self._parse_response(response_text)
            response_tokens = self.token_counter.estimate_tokens(response_text)
            
            # Track tokens
            self.token_counter.add_tokens(prompt_tokens, response_tokens, self.model)
            
            return parsed
            
        except Exception as e:
            logger.error(f"Error during resume analysis: {e}")
            return {"error": f"Analysis failed: {str(e)}"}
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse LLM response and extract JSON.
        Handles various response formats and extraction challenges.
        """
        try:
            # Try direct JSON parsing
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                pass
            
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
            
            # If all parsing fails, return the raw response
            logger.warning("Could not parse response as JSON. Returning raw response.")
            return {"raw_response": response_text}
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            return {"error": "Failed to parse LLM response as JSON", "raw_response": response_text}
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return {"error": f"Response parsing error: {str(e)}", "raw_response": response_text}
    
    # ============ ANALYSIS METHODS ============
    
    def get_strengths(self, resume_text: str) -> Dict[str, Any]:
        """Identify resume strengths."""
        logger.info("Analyzing resume strengths...")
        return self.analyze_resume(resume_text, self.get_strengths_prompt)
    
    def get_weaknesses(self, resume_text: str) -> Dict[str, Any]:
        """Identify resume weaknesses."""
        logger.info("Analyzing resume weaknesses...")
        return self.analyze_resume(resume_text, self.get_weaknesses_prompt)
    
    def get_skills(self, resume_text: str) -> Dict[str, Any]:
        """Extract skills from resume."""
        logger.info("Extracting skills...")
        return self.analyze_resume(resume_text, self.get_skills_extraction_prompt)
    
    def get_improvements(self, resume_text: str) -> Dict[str, Any]:
        """Get improvement suggestions."""
        logger.info("Generating improvement suggestions...")
        return self.analyze_resume(resume_text, self.get_improvement_suggestions_prompt)
    
    def match_job(self, resume_text: str, job_description: str) -> Dict[str, Any]:
        """Match resume against job description."""
        logger.info("Analyzing job match...")
        prompt_func = lambda txt: self.get_job_match_prompt(txt, job_description)
        return self.analyze_resume(resume_text, prompt_func)
    
    def comprehensive_analysis(self, resume_text: str) -> Dict[str, Any]:
        """Perform comprehensive analysis of resume."""
        logger.info("Starting comprehensive resume analysis...")
        
        return {
            "strengths": self.get_strengths(resume_text),
            "weaknesses": self.get_weaknesses(resume_text),
            "skills": self.get_skills(resume_text),
            "suggestions": self.get_improvements(resume_text)
        }
    
    def get_token_stats(self) -> Dict[str, Any]:
        """Get token usage statistics."""
        return self.token_counter.get_stats()


# ============ TESTING ============

if __name__ == "__main__":
    # Test the LLM analyzer
    analyzer = LLMAnalyzer()
    
    # Test connection
    connection_status = analyzer.test_connection()
    print("\n" + "="*60)
    print("CONNECTION TEST")
    print("="*60)
    print(json.dumps(connection_status, indent=2))
    
    if connection_status["status"] == "error":
        print("\n❌ Cannot proceed with analysis. Ollama is not running or not accessible.")
        print(f"Please ensure Ollama is running at {analyzer.ollama_host}")
        exit(1)
    
    # Sample resume
    sample_resume = """
    John Doe
    Software Engineer
    john.doe@example.com | (555) 123-4567 | LinkedIn: linkedin.com/in/johndoe
    
    PROFESSIONAL SUMMARY
    Senior Software Engineer with 5+ years of experience developing scalable web applications.
    Proficient in Python, Django, React, and cloud technologies. Strong background in microservices
    architecture and DevOps practices.
    
    EXPERIENCE
    Senior Software Engineer | Tech Corp | 2020-Present
    - Led development of microservices architecture serving 1M+ users
    - Implemented CI/CD pipeline reducing deployment time by 60%
    - Mentored team of 4 junior developers
    - Technologies: Python, Django, PostgreSQL, Docker, Kubernetes
    
    Software Engineer | Innovate LLC | 2018-2020
    - Built e-commerce platform handling $2M+ in transactions
    - Optimized database queries improving performance by 40%
    - Technologies: Python, Flask, React, AWS
    
    Junior Developer | StartUp Inc | 2017-2018
    - Developed REST APIs for mobile applications
    - Fixed 50+ bugs in production systems
    - Technologies: Python, Django, PostgreSQL
    
    EDUCATION
    B.S. in Computer Science | University of Technology | 2017
    
    SKILLS
    Languages: Python, JavaScript, SQL
    Frameworks: Django, Flask, React, FastAPI
    Tools: Docker, Kubernetes, Git, CI/CD
    Cloud: AWS, Google Cloud
    """
    
    print("\n" + "="*60)
    print("TESTING RESUME ANALYSIS")
    print("="*60)
    
    # Test individual analyses
    print("\n1. STRENGTHS ANALYSIS")
    print("-" * 60)
    strengths = analyzer.get_strengths(sample_resume)
    print(json.dumps(strengths, indent=2))
    
    print("\n2. SKILLS EXTRACTION")
    print("-" * 60)
    skills = analyzer.get_skills(sample_resume)
    print(json.dumps(skills, indent=2))
    
    print("\n3. IMPROVEMENT SUGGESTIONS")
    print("-" * 60)
    suggestions = analyzer.get_improvements(sample_resume)
    print(json.dumps(suggestions, indent=2))
    
    # Token statistics
    print("\n" + "="*60)
    print("TOKEN USAGE STATISTICS")
    print("="*60)
    stats = analyzer.get_token_stats()
    print(json.dumps(stats, indent=2))

