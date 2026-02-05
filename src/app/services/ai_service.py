"""AI service for AWS Bedrock Claude integration."""

import json
import structlog
import boto3
from botocore.config import Config

from app.config import get_settings
from app.models.job import Job
from app.models.user import User

logger = structlog.get_logger()


class AIService:
    """Service for AI-powered features using AWS Bedrock."""

    def __init__(self):
        settings = get_settings()
        self.model_id = settings.bedrock_model_id
        self.max_tokens = settings.bedrock_max_tokens

        # Initialize Bedrock client
        config = Config(
            region_name=settings.aws_region,
            retries={"max_attempts": 3, "mode": "adaptive"},
        )

        self.client = boto3.client(
            "bedrock-runtime",
            config=config,
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
        )

    async def _invoke_claude(
        self, system_prompt: str, user_message: str, max_tokens: int | None = None
    ) -> tuple[str, int, int]:
        """Invoke Claude via Bedrock. Returns (response, input_tokens, output_tokens)."""
        messages = [{"role": "user", "content": user_message}]

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens or self.max_tokens,
            "system": system_prompt,
            "messages": messages,
        }

        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json",
            )

            response_body = json.loads(response["body"].read())
            content = response_body["content"][0]["text"]
            input_tokens = response_body["usage"]["input_tokens"]
            output_tokens = response_body["usage"]["output_tokens"]

            return content, input_tokens, output_tokens

        except Exception as e:
            logger.error("bedrock_invoke_error", error=str(e))
            raise

    async def analyze_resume(self, resume_text: str) -> dict:
        """Analyze a resume and extract structured information."""
        system_prompt = """You are an expert resume analyst and career advisor.
Analyze the provided resume and extract key information in a structured format.
Be thorough but concise. Focus on actionable insights."""

        user_message = f"""Analyze this resume and provide a JSON response with the following structure:
{{
    "summary": "2-3 sentence professional summary",
    "experience_level": "entry|mid|senior|lead|executive",
    "years_of_experience": <number or null>,
    "skills": [
        {{"name": "skill name", "proficiency": "beginner|intermediate|expert", "years": <number or null>}}
    ],
    "suggested_titles": ["title1", "title2", "title3"],
    "industries": ["industry1", "industry2"],
    "strengths": ["strength1", "strength2", "strength3"],
    "improvement_suggestions": ["suggestion1", "suggestion2"],
    "ats_score": <0-100>,
    "ats_suggestions": ["suggestion1", "suggestion2"]
}}

Resume:
{resume_text}"""

        response, _, _ = await self._invoke_claude(system_prompt, user_message)

        # Parse JSON from response
        try:
            # Find JSON in response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except json.JSONDecodeError:
            logger.error("resume_analysis_parse_error", response=response[:500])

        return {
            "summary": response,
            "experience_level": "mid",
            "skills": [],
            "suggested_titles": [],
            "industries": [],
            "strengths": [],
            "improvement_suggestions": [],
            "ats_score": 50,
            "ats_suggestions": [],
        }

    async def match_job(self, user: User, job: Job) -> dict:
        """Calculate match score between user profile and job."""
        # Build user profile context
        skills = [s.name for s in user.skills] if user.skills else []
        prefs = user.preferences

        user_profile = f"""
Title: {user.current_title or 'Not specified'}
Experience: {user.years_of_experience or 'Not specified'} years
Skills: {', '.join(skills) if skills else 'Not specified'}
Location: {user.location or 'Not specified'}
Remote Preference: {user.remote_preference or 'Not specified'}
Desired Salary: {prefs.min_salary if prefs else 'Not specified'} - {prefs.max_salary if prefs else 'Not specified'}
"""

        job_details = f"""
Title: {job.title}
Company: {job.company}
Location: {job.location or 'Not specified'}
Remote: {job.remote_type or ('Yes' if job.is_remote else 'No')}
Experience Level: {job.experience_level or 'Not specified'}
Required Skills: {', '.join(job.required_skills) if job.required_skills else 'Not specified'}
Preferred Skills: {', '.join(job.preferred_skills) if job.preferred_skills else 'Not specified'}
Salary: {job.salary_text or f'{job.salary_min}-{job.salary_max}' if job.salary_min else 'Not specified'}
Description: {job.description[:1500] if job.description else 'Not available'}...
"""

        system_prompt = """You are an expert job matching AI. Analyze the candidate profile
against the job posting and provide a detailed match assessment."""

        user_message = f"""Compare this candidate to the job and provide a JSON response:

CANDIDATE PROFILE:
{user_profile}

JOB POSTING:
{job_details}

Respond with JSON:
{{
    "match_score": <0-100>,
    "recommendation": "strong_match|good_match|consider|weak_match",
    "match_reasons": ["reason1", "reason2", "reason3"],
    "matching_skills": ["skill1", "skill2"],
    "missing_skills": ["skill1", "skill2"],
    "salary_match": true|false|null,
    "location_match": true|false,
    "experience_match": true|false,
    "summary": "1-2 sentence summary of the match"
}}"""

        response, _, _ = await self._invoke_claude(system_prompt, user_message, max_tokens=1000)

        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except json.JSONDecodeError:
            logger.error("job_match_parse_error", response=response[:500])

        return {
            "match_score": 50,
            "recommendation": "consider",
            "match_reasons": [],
            "matching_skills": [],
            "missing_skills": [],
            "salary_match": None,
            "location_match": True,
            "experience_match": True,
            "summary": "Unable to analyze match.",
        }

    async def generate_cover_letter(
        self,
        user: User,
        job: Job,
        resume_text: str | None = None,
        tone: str = "professional",
        custom_instructions: str | None = None,
    ) -> tuple[str, int, int]:
        """Generate a cover letter for a job application."""
        skills = [s.name for s in user.skills] if user.skills else []

        user_context = f"""
Name: {user.full_name}
Title: {user.current_title or 'Job Seeker'}
Experience: {user.years_of_experience or 'Not specified'} years
Skills: {', '.join(skills) if skills else 'Various'}
Summary: {user.summary or 'Not provided'}
"""

        if resume_text:
            user_context += f"\nResume excerpt:\n{resume_text[:2000]}..."

        job_context = f"""
Title: {job.title}
Company: {job.company}
Description: {job.description[:2000] if job.description else 'Not available'}...
Requirements: {job.requirements[:1000] if job.requirements else 'Not specified'}
"""

        tone_instructions = {
            "professional": "Write in a professional, confident tone.",
            "casual": "Write in a friendly, conversational tone while remaining professional.",
            "enthusiastic": "Write with energy and enthusiasm about the opportunity.",
            "formal": "Write in a formal, traditional business letter style.",
        }

        system_prompt = f"""You are an expert career coach and professional writer.
Write a compelling cover letter that highlights the candidate's relevant experience and skills.
{tone_instructions.get(tone, tone_instructions['professional'])}
Keep it concise (3-4 paragraphs). Focus on value the candidate brings to the role."""

        user_message = f"""Write a cover letter for this application.

CANDIDATE:
{user_context}

JOB:
{job_context}

{f'Additional instructions: {custom_instructions}' if custom_instructions else ''}

Write a complete cover letter ready to send. Do not include placeholder text."""

        response, input_tokens, output_tokens = await self._invoke_claude(
            system_prompt, user_message, max_tokens=2000
        )

        return response, input_tokens, output_tokens

    async def answer_application_questions(
        self, user: User, job: Job, questions: list[dict]
    ) -> list[dict]:
        """Generate answers for application questions."""
        skills = [s.name for s in user.skills] if user.skills else []

        user_context = f"""
Name: {user.full_name}
Title: {user.current_title}
Experience: {user.years_of_experience} years
Skills: {', '.join(skills)}
Summary: {user.summary or 'Not provided'}
"""

        questions_text = "\n".join(
            [f"Q{i+1}: {q.get('question', q)}" for i, q in enumerate(questions)]
        )

        system_prompt = """You are helping a job candidate answer application questions.
Provide thoughtful, specific answers that highlight relevant experience and skills.
Keep answers concise but complete. Be honest and authentic."""

        user_message = f"""Answer these application questions for the candidate.

CANDIDATE:
{user_context}

JOB: {job.title} at {job.company}

QUESTIONS:
{questions_text}

Respond with JSON array:
[
    {{"question": "...", "answer": "..."}},
    ...
]"""

        response, _, _ = await self._invoke_claude(system_prompt, user_message)

        try:
            start = response.find("[")
            end = response.rfind("]") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except json.JSONDecodeError:
            logger.error("application_answers_parse_error")

        return []

    async def suggest_skills_to_learn(
        self, user: User, target_jobs: list[Job]
    ) -> dict:
        """Suggest skills to learn based on target jobs."""
        user_skills = [s.name for s in user.skills] if user.skills else []

        job_skills = set()
        for job in target_jobs[:5]:
            if job.required_skills:
                job_skills.update(job.required_skills)
            if job.preferred_skills:
                job_skills.update(job.preferred_skills)

        system_prompt = """You are a career development advisor. Analyze the skill gap
between the candidate's current skills and their target jobs. Provide actionable
recommendations for skill development."""

        user_message = f"""Analyze skill gaps and provide recommendations.

CURRENT SKILLS: {', '.join(user_skills) if user_skills else 'Not specified'}

SKILLS NEEDED FOR TARGET JOBS: {', '.join(job_skills) if job_skills else 'Various'}

Respond with JSON:
{{
    "missing_critical_skills": ["skill1", "skill2"],
    "missing_nice_to_have": ["skill1", "skill2"],
    "recommendations": [
        {{"skill": "skill name", "priority": "high|medium|low", "reason": "why learn this"}}
    ],
    "learning_path": "Brief recommended learning approach"
}}"""

        response, _, _ = await self._invoke_claude(system_prompt, user_message, max_tokens=1500)

        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except json.JSONDecodeError:
            pass

        return {
            "missing_critical_skills": [],
            "missing_nice_to_have": [],
            "recommendations": [],
            "learning_path": "Unable to generate recommendations.",
        }
