import os
import json
import logging
import time
import requests
import hashlib
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


class AnalysisCache:
    """Cache analysis results to avoid re-analyzing the same resume."""
    
    def __init__(self):
        self.cache = {}
        self.cache_dir = "logs/.cache"
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def _generate_key(self, resume_text: str, analysis_type: str) -> str:
        """Generate a cache key based on resume hash and analysis type."""
        resume_hash = hashlib.sha256(resume_text.encode()).hexdigest()
        return f"{analysis_type}_{resume_hash}"
    
    def get(self, resume_text: str, analysis_type: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached analysis result."""
        key = self._generate_key(resume_text, analysis_type)
        
        # Check in-memory cache
        if key in self.cache:
            logger.info(f"Cache hit for {analysis_type}")
            return self.cache[key].copy()
        
        # Check disk cache
        cache_file = os.path.join(self.cache_dir, f"{key}.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    self.cache[key] = data
                    logger.info(f"Cache hit (disk) for {analysis_type}")
                    return data.copy()
            except Exception as e:
                logger.warning(f"Error reading cache file: {e}")
        
        return None
    
    def set(self, resume_text: str, analysis_type: str, result: Dict[str, Any]):
        """Cache an analysis result."""
        key = self._generate_key(resume_text, analysis_type)
        
        # Store in memory
        self.cache[key] = result.copy()
        
        # Store on disk
        try:
            cache_file = os.path.join(self.cache_dir, f"{key}.json")
            with open(cache_file, 'w') as f:
                json.dump(result, f, indent=2)
            logger.info(f"Cached {analysis_type} result")
        except Exception as e:
            logger.warning(f"Error writing cache file: {e}")
    
    def clear(self):
        """Clear all caches."""
        self.cache.clear()
        import shutil
        try:
            if os.path.exists(self.cache_dir):
                shutil.rmtree(self.cache_dir)
                os.makedirs(self.cache_dir)
            logger.info("Analysis cache cleared")
        except Exception as e:
            logger.warning(f"Error clearing cache: {e}")


class LLMAnalyzer:

    def __init__(self, model: Optional[str] = None):
        
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.model = model or os.getenv("OLLAMA_MODEL", "mistral")
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.timeout = int(os.getenv("REQUEST_TIMEOUT", "30"))
        self.temperature = float(os.getenv("TEMPERATURE", "0.2"))
        self.max_tokens = int(os.getenv("MAX_TOKENS", "1024"))
        self.use_langchain = os.getenv("USE_LANGCHAIN", "false").lower() == "true"
        
        self.token_counter = TokenCounter()
        self.cache = AnalysisCache()
        self.client = None
        self.lc_model = None
        
        logger.info(f"Initializing LLMAnalyzer with model: {self.model}, host: {self.ollama_host}")
        self._initialize_client()
        self._initialize_langchain()
    
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

    def _initialize_langchain(self):
        """Initialize LangChain ChatOllama model if enabled."""
        if not self.use_langchain:
            return
        # Disable LangChain pathway to avoid unsupported options and /api/chat warnings
        logger.info("LangChain support disabled to avoid unsupported options; using direct Ollama generate API")
        self.use_langchain = False
        return
        try:
            from langchain_community.chat_models import ChatOllama
            self.lc_model = ChatOllama(
                model=self.model,
                base_url=self.ollama_host,
                temperature=self.temperature,
                num_predict=self.max_tokens,
            )
            logger.info("LangChain ChatOllama initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize LangChain ChatOllama: {e}")
            self.lc_model = None
    
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
        """Generate specialized prompt for identifying resume strengths with confidence scoring."""
        return f"""You are an expert career coach and resume analyzer. 
Analyze the resume and identify 5-7 key strengths in order of importance.

Resume:
{resume_text}

Provide your analysis as a JSON object with the following structure:
{{
    "strengths": [
        {{
            "strength": "specific strength description with clear example",
            "category": "content|formatting|skills|experience|education|achievements",
            "importance": "critical|high|medium",
            "confidence": 0-100,
            "examples": ["quote or bullet from resume showing this"],
            "location": "section or line where found"
        }}
    ],
    "summary": "brief overall strength assessment"
}}

Must-have strong points to look for (cover these explicitly when present):
- Clear formatting and professional presentation
- Relevant experience aligned to likely target roles
- Quantifiable achievements and impact metrics
- Proper use of action verbs
- Relevant certifications and licenses
- Strong educational background
- Domain expertise/industry knowledge

Rules:
- Return 5-7 strengths, sorted by importance/impact (highest first). Do not return an empty list; if evidence is weak, provide best-effort strengths with low confidence and note the uncertainty.
- Include specific examples from the resume text for each strength.
- Include location/section when available.
- Provide a confidence score (0-100) based on evidence clarity.
- Return ONLY valid JSON, no extra text."""
    
    def get_weaknesses_prompt(self, resume_text: str) -> str:
        """Generate specialized prompt for identifying resume weaknesses with severity levels."""
        return f"""You are an expert career coach and resume analyzer.
Analyze the resume and identify 5-7 key weaknesses and areas for improvement.

Resume:
{resume_text}

Provide your analysis as a JSON object with the following structure:
{{
    "weaknesses": [
        {{
            "weakness": "specific issue description with location/context",
            "category": "formatting|content|skills|experience|missing_info|grammar|gaps",
            "severity": "critical|moderate|minor",
            "confidence": 0-100,
            "location": "section where issue was found",
            "impact": "how this affects candidacy",
            "fix": "specific, actionable suggestion to address this issue",
            "examples": ["quote from resume showing the issue"]
        }}
    ],
    "overall_assessment": "general readiness assessment"
}}

Must-check issues (cover when present):
- Missing contact information or critical sections
- Spelling/grammar errors
- Lack of quantifiable achievements
- Irrelevant or outdated information
- Poor formatting or layout problems
- Missing key skills for the target role
- Unexplained employment gaps

Rules:
- Return 5-7 weaknesses with severity (minor|moderate|critical). Do not return an empty list; if evidence is weak, provide best-effort weaknesses with low confidence and note the uncertainty.
- Provide specific examples and locations in the resume for each weakness.
- Include confidence (0-100) per weakness based on evidence clarity.
- Return ONLY valid JSON, no extra text."""
    
    def get_skills_extraction_prompt(self, resume_text: str) -> str:
        """Generate prompt for extracting skills."""
        return f"""You are an expert resume analyst. Carefully extract ALL technical and soft skills from the resume below.

IMPORTANT: Extract EVERY skill mentioned, implied, or demonstrated throughout the entire resume including:
- Programming languages, frameworks, tools, technologies
- Software, platforms, and systems
- Methodologies and practices (Agile, DevOps, CI/CD, etc.)
- Domain expertise and industry knowledge
- Soft skills like leadership, communication, problem-solving
- Skills demonstrated in projects, work experience, and achievements
- Certifications and specialized training

Be thorough and comprehensive - aim to extract at least 10-20 skills if present in the resume.

Resume:
{resume_text}

Provide your analysis as a JSON object with the following structure:
{{"technical_skills": ["skill1", "skill2", "skill3", ...], "soft_skills": ["skill1", "skill2", "skill3", ...]}}

Include all relevant skills found. Return ONLY valid JSON, no additional text."""
    
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
        """Call Ollama API (LangChain if enabled) with retry logic and error handling."""
        if self.use_langchain and self.lc_model:
            return self._call_langchain_with_retry(prompt)

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

    def _call_langchain_with_retry(self, prompt: str) -> Optional[str]:
        """Call Ollama via LangChain ChatOllama with retry logic."""
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Calling LangChain ChatOllama (attempt {attempt + 1}/{self.max_retries})...")
                result = self.lc_model.invoke(prompt)
                # ChatOllama returns an AIMessage; cast to string
                return str(result.content if hasattr(result, "content") else result)
            except Exception as e:
                logger.warning(f"LangChain call failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
        logger.error(f"Failed to get response from LangChain/Ollama after {self.max_retries} attempts")
        return None
    
    def analyze_resume(
        self,
        resume_text: str,
        prompt_func: Callable,
        analysis_type: str = "general",
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Analyze resume using the provided prompt function with caching.
        
        Args:
            resume_text: The resume text to analyze
            prompt_func: Function that takes resume_text and returns a prompt
            analysis_type: Type of analysis for caching (strengths, weaknesses, skills, etc.)
        
        Returns:
            Dictionary with analysis results or error message
        """
        try:
            # Check cache first (if enabled)
            if use_cache:
                cached_result = self.cache.get(resume_text, analysis_type)
                if cached_result:
                    cached_result["cached"] = True
                    return cached_result
            
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

            # If parsing failed and we only have the raw response, surface as an error
            if "raw_response" in parsed and len(parsed.keys()) == 1:
                return {
                    "error": "LLM response was not valid JSON; see raw_response",
                    "raw_response": parsed.get("raw_response")
                }
            
            # Cache the result (only when enabled)
            if use_cache and "error" not in parsed:
                self.cache.set(resume_text, analysis_type, parsed)
                parsed["cached"] = False
            
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
            # 1) Trim code fences and whitespace
            cleaned = response_text.strip()
            cleaned = cleaned.replace("```json", "").replace("```", "").strip()

            # 2) Try direct JSON parsing
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass

            # 3) Try to locate the first JSON object by braces window
            if "{" in cleaned and "}" in cleaned:
                start = cleaned.find("{")
                end = cleaned.rfind("}")
                if start != -1 and end != -1 and end > start:
                    snippet = cleaned[start : end + 1]
                    try:
                        return json.loads(snippet)
                    except json.JSONDecodeError:
                        pass

            # 4) Regex fallback to grab a JSON-ish block
            import re
            json_match = re.search(r'\{[\s\S]*\}', cleaned)
            if json_match:
                json_str = json_match.group(0)
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass

            # If all parsing fails, return the raw response for visibility
            logger.warning("Could not parse response as JSON. Returning raw response.")
            return {"raw_response": response_text}
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            return {"error": "Failed to parse LLM response as JSON", "raw_response": response_text}
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return {"error": f"Response parsing error: {str(e)}", "raw_response": response_text}

    @staticmethod
    def _normalize_strengths(data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize strengths payload to a consistent schema with defaults and confidence bounds."""
        strengths = data.get("strengths", data.get("items", []))
        summary = data.get("summary", "")
        items: List[Dict[str, Any]] = []
        if isinstance(strengths, dict):
            strengths_list = strengths.get("items", [])
            summary = strengths.get("summary", summary)
        else:
            strengths_list = strengths if isinstance(strengths, list) else []

        for item in strengths_list:
            if not isinstance(item, dict):
                continue
            confidence = item.get("confidence", 0)
            try:
                confidence = int(confidence)
            except Exception:
                confidence = 0
            confidence = max(0, min(100, confidence))
            items.append(
                {
                    "strength": item.get("strength", ""),
                    "category": item.get("category", "content"),
                    "importance": item.get("importance", "medium"),
                    "confidence": confidence,
                    "examples": item.get("examples", []),
                    "location": item.get("location", ""),
                }
            )

        return {"summary": summary, "items": items}

    @staticmethod
    def _normalize_weaknesses(data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize weaknesses payload to a consistent schema with defaults and confidence bounds."""
        weaknesses = data.get("weaknesses", data.get("items", []))
        summary = data.get("overall_assessment", data.get("summary", ""))
        items: List[Dict[str, Any]] = []
        if isinstance(weaknesses, dict):
            weaknesses_list = weaknesses.get("items", [])
            summary = weaknesses.get("summary", summary)
        else:
            weaknesses_list = weaknesses if isinstance(weaknesses, list) else []

        for item in weaknesses_list:
            if not isinstance(item, dict):
                continue
            confidence = item.get("confidence", 0)
            try:
                confidence = int(confidence)
            except Exception:
                confidence = 0
            confidence = max(0, min(100, confidence))
            items.append(
                {
                    "weakness": item.get("weakness", ""),
                    "category": item.get("category", "content"),
                    "severity": item.get("severity", "minor"),
                    "location": item.get("location", ""),
                    "impact": item.get("impact", ""),
                    "fix": item.get("fix", ""),
                    "confidence": confidence,
                    "examples": item.get("examples", []),
                }
            )

        return {"summary": summary, "items": items}
    
    # ============ ANALYSIS METHODS ============
    
    def get_strengths(self, resume_text: str) -> Dict[str, Any]:
        """Identify resume strengths with detailed scoring."""
        logger.info("Analyzing resume strengths...")
        result = self.analyze_resume(resume_text, self.get_strengths_prompt, "strengths")
        if "error" in result:
            return result
        return {"strengths": self._normalize_strengths(result), "cached": result.get("cached", False)}
    
    def get_weaknesses(self, resume_text: str) -> Dict[str, Any]:
        """Identify resume weaknesses with severity levels."""
        logger.info("Analyzing resume weaknesses...")
        result = self.analyze_resume(resume_text, self.get_weaknesses_prompt, "weaknesses")
        if "error" in result:
            return result
        return {"weaknesses": self._normalize_weaknesses(result), "cached": result.get("cached", False)}
    
    def get_skills(self, resume_text: str) -> Dict[str, Any]:
        """Extract skills from resume."""
        logger.info("Extracting skills...")
        return self.analyze_resume(resume_text, self.get_skills_extraction_prompt, "skills")
    
    def get_improvements(self, resume_text: str) -> Dict[str, Any]:
        """Get improvement suggestions."""
        logger.info("Generating improvement suggestions...")
        return self.analyze_resume(resume_text, self.get_improvement_suggestions_prompt, "suggestions")
    
    def match_job(self, resume_text: str, job_description: str) -> Dict[str, Any]:
        """Match resume against job description."""
        logger.info("Analyzing job match...")
        prompt_func = lambda txt: self.get_job_match_prompt(txt, job_description)
        return self.analyze_resume(resume_text, prompt_func)
    
    def comprehensive_analysis(self, resume_text: str, use_cache: bool = True) -> Dict[str, Any]:
        """Perform comprehensive analysis of all resume aspects at once with priority ordering."""
        logger.info("Starting comprehensive resume analysis (all aspects)...")
        
        # Check cache first
        if use_cache:
            cached_result = self.cache.get(resume_text, "comprehensive")
            if cached_result:
                cached_result["cached"] = True
                return cached_result
        
        # Define comprehensive prompt for all analyses
        comprehensive_prompt = f"""Analyze this resume comprehensively and provide detailed feedback in the JSON format below.

Resume:
{resume_text}

Return a JSON object with this exact structure (no markdown, pure JSON):
{{
    "strengths": {{
        "summary": "2-3 sentence overall assessment",
        "items": [
            {{
                "strength": "specific strength identified",
                "category": "content|formatting|skills|experience|education|achievements",
                "importance": "critical|high|medium",
                "confidence": 0-100,
                "examples": ["quote from resume showing this strength"],
                "location": "section name where found"
            }}
        ]
    }},
    "weaknesses": {{
        "summary": "2-3 sentence overall assessment",
        "items": [
            {{
                "weakness": "specific weakness identified",
                "category": "formatting|content|skills|experience|missing_info|grammar|gaps",
                "severity": "critical|moderate|minor",
                "location": "section name where issue appears",
                "impact": "how this affects candidacy",
                "fix": "actionable recommendation to fix",
                "confidence": 0-100,
                "examples": ["quote from resume showing the issue"]
            }}
        ]
    }},
    "skills": {{
        "summary": "overview of skill profile",
        "technical": [
            {{"skill": "Python", "proficiency": "advanced|intermediate|beginner", "mentioned_context": "where in resume"}}
        ],
        "soft_skills": [
            {{"skill": "Leadership", "proficiency": "advanced|intermediate|beginner", "mentioned_context": "where in resume"}}
        ]
    }},
    "suggestions": {{
        "summary": "overall improvement roadmap",
        "priority_improvements": [
            {{
                "improvement": "specific actionable step",
                "priority": "high|medium|low",
                "impact": "expected benefit",
                "timeline": "suggested timeframe"
            }}
        ]
    }}
}}

Rules:
- Return 5-7 strengths and 5-7 weaknesses; sort items by importance/severity (highest first). Do not leave lists empty; if evidence is weak, provide best-effort items with low confidence and note the uncertainty.
- For strengths, explicitly consider: clear formatting, relevant experience, quantifiable achievements, action verbs, relevant certifications, strong educational background, domain expertise.
- For weaknesses, explicitly consider: missing contact info, spelling/grammar errors, lack of quantifiable achievements, irrelevant info, poor formatting, missing key skills for target role, unexplained employment gaps.
- For skills: EXTRACT ALL SKILLS mentioned in the resume including programming languages, frameworks, tools, databases, platforms, methodologies, soft skills, domain expertise, certifications, and technologies. Look in Technical Skills section, projects, work experience, and education. Aim for 15-40+ skills total across technical and soft skills. Be comprehensive and thorough.
- Provide examples and locations when available. Use confidence 0-100.
- Ensure valid JSON only."""

        try:
            prompt_tokens = self.token_counter.estimate_tokens(comprehensive_prompt)
            
            # Call Ollama with retry logic
            response_text = self._call_ollama_with_retry(comprehensive_prompt)
            
            if not response_text:
                logger.error("No response from Ollama for comprehensive analysis")
                return {"error": "No response from Ollama. Check connection."}
            
            # Parse the JSON response
            analysis_data = self._parse_response(response_text)

            # Treat unparseable payloads as errors to avoid silently returning empty results
            if "raw_response" in analysis_data and len(analysis_data.keys()) == 1:
                return {
                    "error": "LLM response was not valid JSON; see raw_response",
                    "raw_response": analysis_data.get("raw_response"),
                }

            if "error" in analysis_data:
                logger.error(f"Parse error: {analysis_data.get('error')}")
                return analysis_data
            
            response_tokens = self.token_counter.estimate_tokens(response_text)
            self.token_counter.add_tokens(prompt_tokens, response_tokens, self.model)
            
            # Ensure proper structure with all fields
            comprehensive_result = {
                "strengths": self._normalize_strengths(analysis_data.get("strengths", {})),
                "weaknesses": self._normalize_weaknesses(analysis_data.get("weaknesses", {})),
                "skills": analysis_data.get("skills", {"summary": "", "technical": [], "soft_skills": []}),
                "suggestions": analysis_data.get("suggestions", {"summary": "", "priority_improvements": []}),
                "cached": False
            }

            # Compute single overall score (0-100) using dedicated prompt
            try:
                comprehensive_result["overall_score"] = self.get_overall_score(resume_text)
            except Exception:
                comprehensive_result["overall_score"] = None
            
            # Cache the result
            if use_cache:
                self.cache.set(resume_text, "comprehensive", comprehensive_result)
            
            logger.info("Comprehensive analysis completed successfully")
            return comprehensive_result
        
        except Exception as e:
            logger.error(f"Comprehensive analysis exception: {str(e)}")
            return {"error": f"Comprehensive analysis failed: {str(e)}"}

    def get_overall_score_prompt(self, resume_text: str) -> str:
        return (
            "You are an expert resume reviewer. Read the resume text and output a single integer between 0 and 100 representing the overall resume quality (100 = exceptional, 0 = unusable). "
            "Do not include any words, labels, or explanations—return ONLY the integer. Resume:\n\n" + resume_text
        )

    def get_overall_score(self, resume_text: str) -> Optional[int]:
        """Return a single 0-100 overall score for resume quality."""
        prompt = self.get_overall_score_prompt(resume_text)
        text = self._call_ollama_with_retry(prompt)
        if not text:
            return None
        # Extract first integer in 0-100 range
        import re
        m = re.search(r"\b(100|[0-9]{1,2})\b", text)
        if not m:
            return None
        try:
            val = int(m.group(1))
            return max(0, min(100, val))
        except ValueError:
            return None
    
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
    
    print("\n✅ Connection successful! Analyzer is ready for use.")
    print("\nTo test analysis, use the Streamlit GUI in the Resume Analysis page.")
    print("API is also available for programmatic use:")
    print("  - analyzer.get_strengths(resume_text)")
    print("  - analyzer.get_weaknesses(resume_text)")
    print("  - analyzer.get_skills(resume_text)")
    print("  - analyzer.get_improvements(resume_text)")
    print("  - analyzer.match_job(resume_text, job_description)")
    print("  - analyzer.comprehensive_analysis(resume_text)")


