"""
Groq API agent for LLM-powered analysis and reasoning.
"""
import asyncio
import aiohttp
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from config.settings import settings
from models.schemas import AgentResponse, ValidationResult, CollectionEvent
from utils.logger import get_logger
from utils.helpers import sanitize_input, chunk_text

logger = get_logger("llm_agent")

class LLMAgent:
    """Agent for handling LLM requests via Groq API."""
    
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.base_url = settings.GROQ_API_BASE
        self.timeout = settings.LLM_REQUEST_TIMEOUT
        self.model = "llama3-8b-8192"  # Free tier model
        
    async def analyze_collection_compliance(
        self, 
        collection_event: CollectionEvent,
        satellite_data: Optional[Dict] = None,
        regulatory_data: Optional[Dict] = None
    ) -> AgentResponse:
        """Analyze collection event for compliance using LLM reasoning."""
        try:
            prompt = self._build_compliance_prompt(collection_event, satellite_data, regulatory_data)
            
            logger.info(f"Analyzing compliance for event: {collection_event.event_id}")
            
            response = await self._make_llm_request(prompt)
            
            if response.get("choices") and len(response["choices"]) > 0:
                analysis = response["choices"][0]["message"]["content"]
                structured_result = self._parse_compliance_analysis(analysis, collection_event.event_id)
                
                return AgentResponse(
                    success=True,
                    data=structured_result,
                    message="Compliance analysis completed",
                    source="groq_llm"
                )
            else:
                return AgentResponse(
                    success=False,
                    message="No analysis generated",
                    error="Empty LLM response",
                    source="groq_llm"
                )
                
        except Exception as e:
            logger.error(f"Error in LLM compliance analysis: {str(e)}")
            return AgentResponse(
                success=False,
                message="Failed to analyze compliance",
                error=str(e),
                source="groq_llm"
            )
    
    async def generate_recommendations(
        self, 
        species: str, 
        issues: List[str], 
        context: Dict[str, Any] = None
    ) -> AgentResponse:
        """Generate recommendations based on identified issues."""
        try:
            prompt = self._build_recommendation_prompt(species, issues, context)
            
            logger.info(f"Generating recommendations for {species}")
            
            response = await self._make_llm_request(prompt)
            
            if response.get("choices") and len(response["choices"]) > 0:
                recommendations_text = response["choices"][0]["message"]["content"]
                structured_recs = self._parse_recommendations(recommendations_text)
                
                return AgentResponse(
                    success=True,
                    data={"recommendations": structured_recs},
                    message="Recommendations generated successfully",
                    source="groq_llm"
                )
            else:
                return AgentResponse(
                    success=False,
                    message="No recommendations generated",
                    error="Empty LLM response",
                    source="groq_llm"
                )
                
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            return AgentResponse(
                success=False,
                message="Failed to generate recommendations",
                error=str(e),
                source="groq_llm"
            )
    
    async def explain_regulatory_requirements(
        self, 
        species: str, 
        regulatory_data: Dict[str, Any]
    ) -> AgentResponse:
        """Explain regulatory requirements in simple terms."""
        try:
            prompt = self._build_explanation_prompt(species, regulatory_data)
            
            logger.info(f"Explaining regulatory requirements for {species}")
            
            response = await self._make_llm_request(prompt)
            
            if response.get("choices") and len(response["choices"]) > 0:
                explanation = response["choices"][0]["message"]["content"]
                
                return AgentResponse(
                    success=True,
                    data={"explanation": explanation},
                    message="Regulatory explanation generated",
                    source="groq_llm"
                )
            else:
                return AgentResponse(
                    success=False,
                    message="No explanation generated",
                    error="Empty LLM response",
                    source="groq_llm"
                )
                
        except Exception as e:
            logger.error(f"Error explaining requirements: {str(e)}")
            return AgentResponse(
                success=False,
                message="Failed to explain requirements",
                error=str(e),
                source="groq_llm"
            )
    
    async def _make_llm_request(self, prompt: str) -> Dict[str, Any]:
        """Make request to Groq API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert in Ayurvedic herbs, sustainable harvesting practices, and Indian regulatory compliance for medicinal plants. Provide accurate, practical advice based on NMPB guidelines and traditional knowledge."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,
            "max_tokens": 1000,
            "top_p": 0.9
        }
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
            async with session.post(f"{self.base_url}/chat/completions", json=payload, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"Groq API error {response.status}: {error_text}")
                    raise Exception(f"LLM API request failed with status {response.status}")
    
    def _build_compliance_prompt(
        self, 
        collection_event: CollectionEvent,
        satellite_data: Optional[Dict] = None,
        regulatory_data: Optional[Dict] = None
    ) -> str:
        """Build prompt for compliance analysis."""
        prompt_parts = [
            f"Analyze the following Ayurvedic herb collection event for compliance:",
            f"",
            f"COLLECTION DETAILS:",
            f"Species: {collection_event.species.common_name} ({collection_event.species.scientific_name})",
            f"Collection Date: {collection_event.timestamp.strftime('%Y-%m-%d')}",
            f"Location: {collection_event.location.latitude}, {collection_event.location.longitude}",
            f"Quantity: {collection_event.quantity_kg} kg",
            f"Collector: {collection_event.collector.name}",
            f"Conservation Status: {collection_event.species.conservation_status.value}",
            f"Allowed Harvest Seasons: {', '.join([s.value for s in collection_event.species.harvest_seasons])}",
        ]
        
        if satellite_data:
            prompt_parts.extend([
                f"",
                f"SATELLITE VALIDATION:",
                f"Validation Score: {satellite_data.get('validation_score', 'N/A')}",
                f"Cloud Cover: {satellite_data.get('cloud_cover', 'N/A')}%",
                f"Vegetation Index: {satellite_data.get('vegetation_index', 'N/A')}",
                f"Land Use Type: {satellite_data.get('land_use_type', 'N/A')}",
            ])
        
        if regulatory_data:
            prompt_parts.extend([
                f"",
                f"REGULATORY CONTEXT:",
                f"Requirements: {', '.join(regulatory_data.get('requirements', []))}",
                f"Restrictions: {', '.join(regulatory_data.get('restrictions', []))}",
                f"Authorities: {', '.join(regulatory_data.get('authorities', []))}",
            ])
        
        prompt_parts.extend([
            f"",
            f"Please analyze this collection event and provide:",
            f"1. COMPLIANCE_STATUS: compliant/non_compliant/requires_review",
            f"2. CONFIDENCE_SCORE: 0.0 to 1.0",
            f"3. ISSUES: List any compliance issues found",
            f"4. WARNINGS: List any warnings or concerns",
            f"5. RECOMMENDATIONS: Suggest improvements",
            f"6. NEXT_STEPS: What should be done next",
            f"",
            f"Consider seasonal restrictions, conservation status, harvesting best practices, and regulatory requirements.",
            f"Format your response with clear sections using the labels above."
        ])
        
        return "\n".join(prompt_parts)
    
    def _build_recommendation_prompt(
        self, 
        species: str, 
        issues: List[str], 
        context: Dict[str, Any] = None
    ) -> str:
        """Build prompt for generating recommendations."""
        prompt_parts = [
            f"Generate specific, actionable recommendations for improving Ayurvedic herb collection practices:",
            f"",
            f"SPECIES: {species}",
            f"IDENTIFIED ISSUES:",
        ]
        
        for i, issue in enumerate(issues, 1):
            prompt_parts.append(f"{i}. {issue}")
        
        if context:
            prompt_parts.extend([
                f"",
                f"ADDITIONAL CONTEXT:",
                json.dumps(context, indent=2, default=str)
            ])
        
        prompt_parts.extend([
            f"",
            f"Provide specific recommendations that address each issue.",
            f"Focus on practical steps that collectors, farmers, and processors can take.",
            f"Consider sustainability, quality, regulatory compliance, and traditional knowledge.",
            f"Format as numbered recommendations with clear action steps."
        ])
        
        return "\n".join(prompt_parts)
    
    def _build_explanation_prompt(
        self, 
        species: str, 
        regulatory_data: Dict[str, Any]
    ) -> str:
        """Build prompt for explaining regulatory requirements."""
        prompt_parts = [
            f"Explain the regulatory requirements for {species} in simple, clear terms:",
            f"",
            f"REGULATORY INFORMATION:",
            json.dumps(regulatory_data, indent=2, default=str),
            f"",
            f"Please provide a clear explanation that covers:",
            f"1. Who regulates this species",
            f"2. What permits or licenses are needed",
            f"3. When harvesting is allowed/restricted",
            f"4. Where harvesting is permitted",
            f"5. Quality standards that must be met",
            f"6. Conservation considerations",
            f"",
            f"Use simple language suitable for farmers and collectors.",
            f"Focus on practical compliance steps."
        ]
        
        return "\n".join(prompt_parts)
    
    def _parse_compliance_analysis(self, analysis_text: str, event_id: str) -> Dict[str, Any]:
        """Parse LLM compliance analysis into structured data."""
        result = {
            "event_id": event_id,
            "validation_timestamp": datetime.now(),
            "overall_status": "pending",
            "confidence_score": 0.5,
            "compliance_summary": "",
            "recommendations": [],
            "warnings": [],
            "next_steps": [],
            "issues": []
        }
        
        lines = analysis_text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Identify sections
            if line.upper().startswith('COMPLIANCE_STATUS:'):
                status = line.split(':', 1)[1].strip().lower()
                result["overall_status"] = status
            elif line.upper().startswith('CONFIDENCE_SCORE:'):
                try:
                    score = float(line.split(':', 1)[1].strip())
                    result["confidence_score"] = max(0.0, min(1.0, score))
                except:
                    pass
            elif line.upper().startswith('ISSUES:'):
                current_section = "issues"
            elif line.upper().startswith('WARNINGS:'):
                current_section = "warnings"
            elif line.upper().startswith('RECOMMENDATIONS:'):
                current_section = "recommendations"
            elif line.upper().startswith('NEXT_STEPS:'):
                current_section = "next_steps"
            elif current_section and line:
                # Clean up numbered lists
                clean_line = line.lstrip('0123456789.- ').strip()
                if clean_line:
                    result[current_section].append(clean_line)
        
        # Generate summary
        if result["overall_status"] == "compliant":
            result["compliance_summary"] = "✅ Collection event is compliant with regulations"
        elif result["overall_status"] == "non_compliant":
            result["compliance_summary"] = "❌ Collection event has compliance violations"
        else:
            result["compliance_summary"] = "⚠️ Collection event requires further review"
        
        return result
    
    def _parse_recommendations(self, recommendations_text: str) -> List[str]:
        """Parse LLM recommendations into list."""
        lines = recommendations_text.split('\n')
        recommendations = []
        
        for line in lines:
            line = line.strip()
            if line and not line.upper().startswith('RECOMMENDATIONS'):
                # Clean up numbered lists
                clean_line = line.lstrip('0123456789.- ').strip()
                if clean_line and len(clean_line) > 10:  # Filter out very short lines
                    recommendations.append(clean_line)
        
        return recommendations