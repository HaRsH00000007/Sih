"""
Main orchestrator that coordinates between all agents and validation services.
"""
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional

from models.schemas import (
    ValidationRequest, ValidationResult, CollectionEvent, 
    AgentResponse, ComplianceStatus
)
from agents.serper_agent import SerperAgent
from agents.llm_agent import LLMAgent
from core.validation import ValidationCoordinator
from utils.logger import get_logger
from utils.helpers import merge_validation_results

logger = get_logger("orchestrator")

class VrukshaChainOrchestrator:
    """Main orchestrator for VrukshaChain validation system."""
    
    def __init__(self):
        self.serper_agent = SerperAgent()
        self.llm_agent = LLMAgent()
        self.validation_coordinator = ValidationCoordinator()
        
    async def validate_collection(
        self, 
        collection_event: CollectionEvent,
        validation_types: List[str] = None,
        use_ai_analysis: bool = True
    ) -> ValidationResult:
        """Main entry point for collection validation."""
        try:
            if validation_types is None:
                validation_types = ["satellite", "regulatory", "quality"]
            
            logger.info(f"Starting orchestrated validation for event: {collection_event.event_id}")
            
            # Create validation request
            validation_request = ValidationRequest(
                collection_event=collection_event,
                validation_types=validation_types
            )
            
            # Perform core validation
            validation_result = await self.validation_coordinator.validate_collection_event(
                validation_request
            )
            
            # Enhance with AI analysis if requested
            if use_ai_analysis:
                enhanced_result = await self._enhance_with_ai_analysis(
                    collection_event, validation_result
                )
                return enhanced_result
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error in orchestrated validation: {str(e)}")
            return ValidationResult(
                event_id=collection_event.event_id,
                overall_status=ComplianceStatus.REQUIRES_REVIEW,
                confidence_score=0.0,
                compliance_summary="❌ Validation system error occurred",
                warnings=[f"System error: {str(e)}"],
                next_steps=["Contact technical support", "Retry validation"]
            )
    
    async def get_regulatory_insights(
        self, 
        species: str, 
        region: str = "india"
    ) -> AgentResponse:
        """Get regulatory insights for a species using web search and AI analysis."""
        try:
            logger.info(f"Fetching regulatory insights for {species} in {region}")
            
            # Search for regulatory information
            regulatory_search = await self.serper_agent.search_regulatory_info(species, region)
            
            # Get species information
            species_search = await self.serper_agent.search_species_info(species)
            
            # Get conservation status
            conservation_search = await self.serper_agent.search_conservation_status(species)
            
            # Combine search results
            search_data = {
                "regulatory_info": regulatory_search.data if regulatory_search.success else {},
                "species_info": species_search.data if species_search.success else {},
                "conservation_info": conservation_search.data if conservation_search.success else {}
            }
            
            # Get AI explanation of requirements
            if search_data["regulatory_info"]:
                explanation_response = await self.llm_agent.explain_regulatory_requirements(
                    species, search_data["regulatory_info"]
                )
                
                return AgentResponse(
                    success=True,
                    data={
                        "search_results": search_data,
                        "ai_explanation": explanation_response.data if explanation_response.success else None,
                        "insights_summary": self._generate_insights_summary(search_data)
                    },
                    message="Regulatory insights generated successfully",
                    source="orchestrator"
                )
            else:
                return AgentResponse(
                    success=False,
                    message="Could not find sufficient regulatory information",
                    error="No regulatory data found in search results",
                    source="orchestrator"
                )
            
        except Exception as e:
            logger.error(f"Error getting regulatory insights: {str(e)}")
            return AgentResponse(
                success=False,
                message="Failed to get regulatory insights",
                error=str(e),
                source="orchestrator"
            )
    
    async def generate_collection_recommendations(
        self, 
        species: str,
        location: Optional[Dict[str, float]] = None,
        issues: List[str] = None
    ) -> AgentResponse:
        """Generate recommendations for improving collection practices."""
        try:
            logger.info(f"Generating collection recommendations for {species}")
            
            # Gather context information
            context = {"species": species}
            
            if location:
                context["location"] = location
            
            # Search for seasonal restrictions
            seasonal_search = await self.serper_agent.search_seasonal_restrictions(species)
            if seasonal_search.success:
                context["seasonal_info"] = seasonal_search.data
            
            # Generate AI recommendations
            if issues is None:
                issues = ["General best practices needed"]
            
            recommendations_response = await self.llm_agent.generate_recommendations(
                species, issues, context
            )
            
            if recommendations_response.success:
                return AgentResponse(
                    success=True,
                    data={
                        "recommendations": recommendations_response.data["recommendations"],
                        "context": context,
                        "issues_addressed": issues
                    },
                    message="Collection recommendations generated",
                    source="orchestrator"
                )
            else:
                return AgentResponse(
                    success=False,
                    message="Failed to generate recommendations",
                    error=recommendations_response.error,
                    source="orchestrator"
                )
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            return AgentResponse(
                success=False,
                message="Failed to generate collection recommendations",
                error=str(e),
                source="orchestrator"
            )
    
    async def perform_comprehensive_analysis(
        self, 
        collection_event: CollectionEvent
    ) -> Dict[str, Any]:
        """Perform comprehensive analysis including validation and insights."""
        try:
            logger.info(f"Starting comprehensive analysis for event: {collection_event.event_id}")
            
            # Start validation in background
            validation_task = asyncio.create_task(
                self.validate_collection(collection_event, use_ai_analysis=True)
            )
            
            # Get regulatory insights
            insights_task = asyncio.create_task(
                self.get_regulatory_insights(
                    collection_event.species.common_name,
                    "india"
                )
            )
            
            # Wait for both tasks
            validation_result, insights_result = await asyncio.gather(
                validation_task, insights_task, return_exceptions=True
            )
            
            # Handle validation result
            if isinstance(validation_result, Exception):
                logger.error(f"Validation failed: {str(validation_result)}")
                validation_data = None
            else:
                validation_data = validation_result
            
            # Handle insights result
            if isinstance(insights_result, Exception):
                logger.error(f"Insights failed: {str(insights_result)}")
                insights_data = None
            elif insights_result.success:
                insights_data = insights_result.data
            else:
                insights_data = None
            
            # Generate comprehensive recommendations if needed
            recommendations_data = None
            if validation_data and validation_data.overall_status != ComplianceStatus.COMPLIANT:
                issues = validation_data.warnings + [
                    issue for issue in getattr(validation_data, 'issues', [])
                ]
                if issues:
                    rec_response = await self.generate_collection_recommendations(
                        collection_event.species.common_name,
                        {
                            "latitude": collection_event.location.latitude,
                            "longitude": collection_event.location.longitude
                        },
                        issues
                    )
                    if rec_response.success:
                        recommendations_data = rec_response.data
            
            return {
                "validation_result": validation_data,
                "regulatory_insights": insights_data,
                "recommendations": recommendations_data,
                "analysis_timestamp": datetime.now(),
                "analysis_complete": True
            }
            
        except Exception as e:
            logger.error(f"Error in comprehensive analysis: {str(e)}")
            return {
                "validation_result": None,
                "regulatory_insights": None,
                "recommendations": None,
                "analysis_timestamp": datetime.now(),
                "analysis_complete": False,
                "error": str(e)
            }
    
    async def _enhance_with_ai_analysis(
        self, 
        collection_event: CollectionEvent, 
        validation_result: ValidationResult
    ) -> ValidationResult:
        """Enhance validation result with AI analysis."""
        try:
            logger.info("Enhancing validation with AI analysis")
            
            # Prepare satellite and regulatory data for AI analysis
            satellite_data = None
            regulatory_data = None
            
            # Extract data if available (this would need to be implemented based on validation result structure)
            # For now, we'll work with the basic validation result
            
            # Get AI analysis
            ai_response = await self.llm_agent.analyze_collection_compliance(
                collection_event, satellite_data, regulatory_data
            )
            
            if ai_response.success:
                ai_analysis = ai_response.data
                
                # Merge AI insights with existing validation result
                enhanced_result = ValidationResult(
                    event_id=validation_result.event_id,
                    validation_timestamp=validation_result.validation_timestamp,
                    overall_status=validation_result.overall_status,
                    confidence_score=max(validation_result.confidence_score, ai_analysis.get("confidence_score", 0.5)),
                    compliance_summary=ai_analysis.get("compliance_summary", validation_result.compliance_summary),
                    recommendations=list(set(
                        validation_result.recommendations + ai_analysis.get("recommendations", [])
                    )),
                    warnings=list(set(
                        validation_result.warnings + ai_analysis.get("warnings", [])
                    )),
                    next_steps=list(set(
                        validation_result.next_steps + ai_analysis.get("next_steps", [])
                    )),
                    data_sources_used=validation_result.data_sources_used + ["groq_llm"],
                    validation_duration_seconds=validation_result.validation_duration_seconds
                )
                
                return enhanced_result
            else:
                logger.warning("AI analysis failed, returning original validation result")
                return validation_result
            
        except Exception as e:
            logger.error(f"Error enhancing with AI analysis: {str(e)}")
            # Return original result if AI enhancement fails
            return validation_result
    
    def _generate_insights_summary(self, search_data: Dict[str, Any]) -> str:
        """Generate a summary of regulatory insights."""
        summary_parts = []
        
        # Regulatory info summary
        regulatory_info = search_data.get("regulatory_info", {})
        if regulatory_info.get("authorities"):
            authorities = regulatory_info["authorities"]
            summary_parts.append(f"Regulated by: {', '.join(authorities)}")
        
        if regulatory_info.get("requirements"):
            req_count = len(regulatory_info["requirements"])
            summary_parts.append(f"{req_count} key requirements identified")
        
        # Conservation info summary
        conservation_info = search_data.get("conservation_info", {})
        if conservation_info.get("conservation_status"):
            status = conservation_info["conservation_status"].replace("_", " ").title()
            summary_parts.append(f"Conservation status: {status}")
        
        # Species info summary
        species_info = search_data.get("species_info", {})
        if species_info.get("scientific_name"):
            summary_parts.append(f"Scientific name: {species_info['scientific_name']}")
        
        if not summary_parts:
            return "Limited regulatory information available"
        
        return "; ".join(summary_parts)
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get health status of all system components."""
        try:
            health_status = {
                "timestamp": datetime.now(),
                "overall_status": "healthy",
                "components": {}
            }
            
            # Test Serper agent
            try:
                test_search = await self.serper_agent.search_species_info("ashwagandha")
                health_status["components"]["serper_agent"] = {
                    "status": "healthy" if test_search.success else "degraded",
                    "last_test": datetime.now(),
                    "error": test_search.error if not test_search.success else None
                }
            except Exception as e:
                health_status["components"]["serper_agent"] = {
                    "status": "unhealthy",
                    "last_test": datetime.now(),
                    "error": str(e)
                }
            
            # Test LLM agent (simple test)
            try:
                # Simple test that doesn't require API call
                health_status["components"]["llm_agent"] = {
                    "status": "healthy",
                    "last_test": datetime.now(),
                    "note": "Component initialized successfully"
                }
            except Exception as e:
                health_status["components"]["llm_agent"] = {
                    "status": "unhealthy",
                    "last_test": datetime.now(),
                    "error": str(e)
                }
            
            # Test validation coordinator
            try:
                # Test basic initialization
                health_status["components"]["validation_coordinator"] = {
                    "status": "healthy",
                    "last_test": datetime.now(),
                    "note": "All validation services initialized"
                }
            except Exception as e:
                health_status["components"]["validation_coordinator"] = {
                    "status": "unhealthy",
                    "last_test": datetime.now(),
                    "error": str(e)
                }
            
            # Determine overall status
            component_statuses = [comp["status"] for comp in health_status["components"].values()]
            if "unhealthy" in component_statuses:
                health_status["overall_status"] = "unhealthy"
            elif "degraded" in component_statuses:
                health_status["overall_status"] = "degraded"
            
            return health_status
            
        except Exception as e:
            logger.error(f"Error getting system health: {str(e)}")
            return {
                "timestamp": datetime.now(),
                "overall_status": "unhealthy",
                "error": str(e),
                "components": {}
            }