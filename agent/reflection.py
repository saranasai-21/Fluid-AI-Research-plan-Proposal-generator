"""
Fluid AI — Reflection / Self-Check Module
After content generation, this module sends the output back to the LLM
for a quality review. If quality is below threshold, it triggers a
refinement pass to improve the content.
"""

from __future__ import annotations

import logging
from typing import Optional

from agent.llm_client import LLMClient
from models.schemas import ReflectionResult, StepResult, StepStatus, ExecutionPlan
from config import REFLECTION_QUALITY_THRESHOLD, MAX_REFINEMENT_PASSES

logger = logging.getLogger("fluid_ai.reflection")

# ─── Reflection Prompt ───────────────────────────────────────────────────────

REFLECTION_SYSTEM_PROMPT = """You are a quality review agent. Your job is to evaluate generated 
business document content for quality, completeness, and professionalism.

Evaluate the content on these criteria:
1. **Completeness**: Does the content cover all aspects of the original request?
2. **Coherence**: Is the content logically organized and well-structured?
3. **Professionalism**: Is the tone appropriate for a business document?
4. **Specificity**: Does the content include specific details, numbers, and actionable items?
5. **Accuracy**: Are the claims and suggestions reasonable and realistic?

Respond with a JSON object:
{
    "quality_score": <float 1.0-10.0>,
    "completeness": "<assessment string>",
    "coherence": "<assessment string>",
    "improvements": ["<improvement 1>", "<improvement 2>", ...]
}

Be honest but constructive. A score of 7+ means the content is ready for document generation."""

REFINEMENT_SYSTEM_PROMPT = """You are a content refinement agent. You have been given business 
document content that needs improvement based on specific feedback.

Your task:
1. Address each improvement suggestion
2. Enhance the content while maintaining its structure
3. Add more specific details, data, or examples where suggested
4. Improve professional tone and clarity
5. Return the COMPLETE refined content (not just the changes)

Return the full refined content in markdown format. Do not add meta-commentary."""


class Reflector:
    """
    Reviews generated content for quality and optionally refines it.
    Implements the self-check pattern for autonomous agent improvement.
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or LLMClient()

    def review(
        self,
        plan: ExecutionPlan,
        step_results: list[StepResult],
        user_request: str,
    ) -> ReflectionResult:
        """
        Review the generated content and optionally refine it.

        Args:
            plan: The execution plan that was followed.
            step_results: Results from all executed steps.
            user_request: The original user request.

        Returns:
            ReflectionResult with quality score and optionally refined content.
        """
        # Assemble all generated content
        content = self._assemble_content(step_results)
        if not content.strip():
            return ReflectionResult(
                quality_score=1.0,
                completeness="No content was generated.",
                coherence="N/A",
                improvements=["Regenerate all content — no output was produced."],
            )

        logger.info("Starting quality review of generated content...")

        # Step 1: Get quality assessment
        review = self._assess_quality(content, user_request, plan)
        logger.info(f"Quality score: {review.quality_score}/10")

        # Step 2: If below threshold, refine
        if review.quality_score < REFLECTION_QUALITY_THRESHOLD:
            logger.info(
                f"Quality ({review.quality_score}) below threshold "
                f"({REFLECTION_QUALITY_THRESHOLD}). Running refinement..."
            )
            for pass_num in range(1, MAX_REFINEMENT_PASSES + 1):
                logger.info(f"Refinement pass {pass_num}/{MAX_REFINEMENT_PASSES}")
                refined = self._refine_content(
                    content, review.improvements, user_request, plan
                )
                if refined:
                    review.refined_content = refined
                    logger.info("Refinement complete — using improved content")
                    break
        else:
            logger.info("Quality is above threshold — no refinement needed")

        return review

    def _assess_quality(
        self,
        content: str,
        user_request: str,
        plan: ExecutionPlan,
    ) -> ReflectionResult:
        """Send content to LLM for quality assessment."""
        user_prompt = (
            f"## Original Request\n{user_request}\n\n"
            f"## Document Type\n{plan.document_type}: {plan.document_title}\n\n"
            f"## Generated Content to Review\n{content}\n\n"
            f"Please evaluate this content and respond with your JSON assessment."
        )

        try:
            raw = self.llm.chat_json(
                system_prompt=REFLECTION_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.3,  # Low temperature for consistent evaluation
            )
            return ReflectionResult(**raw)
        except Exception as e:
            logger.warning(f"Quality assessment failed: {e}. Defaulting to pass.")
            return ReflectionResult(
                quality_score=7.5,
                completeness="Assessment could not be completed — defaulting to acceptable.",
                coherence="Assessment could not be completed.",
                improvements=[],
            )

    def _refine_content(
        self,
        content: str,
        improvements: list[str],
        user_request: str,
        plan: ExecutionPlan,
    ) -> Optional[str]:
        """Refine the content based on improvement suggestions."""
        improvements_text = "\n".join(f"- {imp}" for imp in improvements)
        user_prompt = (
            f"## Original Request\n{user_request}\n\n"
            f"## Document: {plan.document_title}\n\n"
            f"## Current Content\n{content}\n\n"
            f"## Required Improvements\n{improvements_text}\n\n"
            f"Please refine and return the COMPLETE improved content."
        )

        try:
            refined = self.llm.chat(
                system_prompt=REFINEMENT_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.6,
                max_tokens=4096,
            )
            return refined
        except Exception as e:
            logger.warning(f"Refinement failed: {e}. Using original content.")
            return None

    @staticmethod
    def _assemble_content(step_results: list[StepResult]) -> str:
        """Assemble content from all completed steps."""
        parts = []
        for result in step_results:
            if result.status == StepStatus.COMPLETED and result.content:
                parts.append(result.content)
        return "\n\n---\n\n".join(parts)
