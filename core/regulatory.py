"""
Regulatory compliance checking and validation logic.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json

from config.settings import settings
from models.schemas import RegulatoryInfo, ComplianceStatus, AgentResponse, HerbSpecies
from utils.logger import get_logger
from utils.helpers import calculate_harvest_season, is_harvest_season_valid

logger = get_logger("regulatory")

class RegulatoryService:
    """Service for checking regulatory compliance for Ayurvedic herbs."""
    
    def __init__(self):
        self.cache_hours = settings.REGULATORY_CACHE_HOURS
        self._compliance_cache = {}
        
    async def check_species_compliance(
        self, 
        species: HerbSpecies, 
        harvest_date: datetime,
        location: Dict[str, float] = None,
        quantity_kg: float = None
    ) -> AgentResponse:
        """Check regulatory compliance for a specific species."""
        try:
            logger.info(f"Checking compliance for species: {species.common_name}")
            
            compliance_results = []
            
            # Check conservation status compliance
            conservation_check = await self._check_conservation_status(species)
            compliance_results.append(conservation_check)
            
            # Check seasonal harvesting compliance
            seasonal_check = await self._check_seasonal_restrictions(species, harvest_date)
            compliance_results.append(seasonal_check)
            
            # Check quantity limitations
            if quantity_kg:
                quantity_check = await self._check_quantity_limits(species, quantity_kg)
                compliance_results.append(quantity_check)
            
            # Check regional restrictions
            if location:
                regional_check = await self._check_regional_restrictions(species, location)
                compliance_results.append(regional_check)
            
            # Check permit requirements
            permit_check = await self._check_permit_requirements(species)
            compliance_results.append(permit_check)
            
            # Aggregate results
            overall_compliance = self._aggregate_compliance_results(compliance_results)
            
            return AgentResponse(
                success=True,
                data={
                    "overall_compliance": overall_compliance,
                    "detailed_checks": compliance_results,
                    "regulatory_summary": self._generate_compliance_summary(overall_compliance)
                },
                message="Regulatory compliance check completed",
                source="regulatory_service"
            )
            
        except Exception as e:
            logger.error(f"Error checking species compliance: {str(e)}")
            return AgentResponse(
                success=False,
                message="Failed to check regulatory compliance",
                error=str(e),
                source="regulatory_service"
            )
    
    async def get_regulatory_requirements(self, species: str, region: str = "india") -> AgentResponse:
        """Get detailed regulatory requirements for a species."""
        try:
            logger.info(f"Fetching regulatory requirements for {species} in {region}")
            
            # Check cache first
            cache_key = f"{species}_{region}_requirements"
            if cache_key in self._compliance_cache:
                cache_time, data = self._compliance_cache[cache_key]
                if datetime.now() - cache_time < timedelta(hours=self.cache_hours):
                    logger.info("Using cached regulatory requirements")
                    return AgentResponse(
                        success=True,
                        data=data,
                        message="Regulatory requirements retrieved (cached)",
                        source="regulatory_service"
                    )
            
            # Fetch fresh requirements
            requirements = await self._fetch_species_requirements(species, region)
            
            # Cache result
            self._compliance_cache[cache_key] = (datetime.now(), requirements)
            
            return AgentResponse(
                success=True,
                data=requirements,
                message="Regulatory requirements retrieved",
                source="regulatory_service"
            )
            
        except Exception as e:
            logger.error(f"Error fetching regulatory requirements: {str(e)}")
            return AgentResponse(
                success=False,
                message="Failed to fetch regulatory requirements",
                error=str(e),
                source="regulatory_service"
            )
    
    async def validate_quality_standards(
        self, 
        species: str, 
        quality_metrics: Dict[str, float]
    ) -> AgentResponse:
        """Validate quality metrics against regulatory standards."""
        try:
            logger.info(f"Validating quality standards for {species}")
            
            validation_results = []
            
            # Check against defined quality standards
            standards = settings.QUALITY_STANDARDS
            
            for parameter, value in quality_metrics.items():
                if parameter in standards:
                    standard = standards[parameter]
                    is_compliant = self._check_quality_parameter(parameter, value, standard)
                    
                    validation_results.append({
                        "parameter": parameter,
                        "value": value,
                        "standard": standard,
                        "compliant": is_compliant,
                        "status": "compliant" if is_compliant else "non_compliant"
                    })
            
            # Calculate overall compliance
            compliant_count = sum(1 for r in validation_results if r["compliant"])
            overall_compliant = compliant_count == len(validation_results)
            
            return AgentResponse(
                success=True,
                data={
                    "overall_compliant": overall_compliant,
                    "compliance_rate": compliant_count / len(validation_results) if validation_results else 0,
                    "parameter_results": validation_results,
                    "summary": self._generate_quality_summary(validation_results)
                },
                message="Quality standards validation completed",
                source="regulatory_service"
            )
            
        except Exception as e:
            logger.error(f"Error validating quality standards: {str(e)}")
            return AgentResponse(
                success=False,
                message="Failed to validate quality standards",
                error=str(e),
                source="regulatory_service"
            )
    
    async def _check_conservation_status(self, species: HerbSpecies) -> Dict[str, Any]:
        """Check conservation status compliance."""
        conservation_status = species.conservation_status.value
        
        compliance_info = {
            "check_type": "conservation_status",
            "species": species.common_name,
            "current_status": conservation_status,
            "compliance_status": ComplianceStatus.COMPLIANT,
            "requirements": [],
            "restrictions": [],
            "recommendations": []
        }
        
        if conservation_status in ["critically_endangered", "endangered"]:
            compliance_info["compliance_status"] = ComplianceStatus.NON_COMPLIANT
            compliance_info["restrictions"].append("Collection prohibited for endangered species")
            compliance_info["requirements"].append("Special permit required from forest department")
            compliance_info["recommendations"].append("Consider cultivation instead of wild collection")
        
        elif conservation_status == "vulnerable":
            compliance_info["compliance_status"] = ComplianceStatus.REQUIRES_REVIEW
            compliance_info["restrictions"].append("Limited collection allowed with permits")
            compliance_info["requirements"].append("Sustainable harvesting plan required")
            compliance_info["recommendations"].append("Monitor collection impact on population")
        
        elif conservation_status == "near_threatened":
            compliance_info["requirements"].append("Follow sustainable collection practices")
            compliance_info["recommendations"].append("Contribute to conservation efforts")
        
        else:  # least_concern, data_deficient
            compliance_info["requirements"].append("Follow standard collection guidelines")
            compliance_info["recommendations"].append("Monitor species health during collection")
        
        return compliance_info
    
    async def _check_seasonal_restrictions(
        self, 
        species: HerbSpecies, 
        harvest_date: datetime
    ) -> Dict[str, Any]:
        """Check seasonal harvesting restrictions."""
        current_season = calculate_harvest_season(harvest_date)
        allowed_seasons = [season.value for season in species.harvest_seasons]
        
        is_compliant = current_season in allowed_seasons
        
        compliance_info = {
            "check_type": "seasonal_restrictions",
            "species": species.common_name,
            "harvest_date": harvest_date.strftime("%Y-%m-%d"),
            "current_season": current_season,
            "allowed_seasons": allowed_seasons,
            "compliance_status": ComplianceStatus.COMPLIANT if is_compliant else ComplianceStatus.NON_COMPLIANT,
            "requirements": [],
            "restrictions": [],
            "recommendations": []
        }
        
        if not is_compliant:
            compliance_info["restrictions"].append(f"Harvesting not allowed during {current_season}")
            compliance_info["requirements"].append(f"Wait for appropriate season: {', '.join(allowed_seasons)}")
            compliance_info["recommendations"].append("Plan collection during optimal seasons for better quality")
        else:
            compliance_info["requirements"].append("Continue following seasonal guidelines")
            compliance_info["recommendations"].append("Harvest during peak quality period within season")
        
        return compliance_info
    
    async def _check_quantity_limits(
        self, 
        species: HerbSpecies, 
        quantity_kg: float
    ) -> Dict[str, Any]:
        """Check quantity limitations based on conservation status."""
        # Define quantity limits based on conservation status
        quantity_limits = {
            "critically_endangered": 0,
            "endangered": 0,
            "vulnerable": 10,  # kg per collection event
            "near_threatened": 50,
            "least_concern": 100,
            "data_deficient": 25
        }
        
        conservation_status = species.conservation_status.value
        max_allowed = quantity_limits.get(conservation_status, 50)
        
        is_compliant = quantity_kg <= max_allowed
        
        compliance_info = {
            "check_type": "quantity_limits",
            "species": species.common_name,
            "requested_quantity": quantity_kg,
            "maximum_allowed": max_allowed,
            "conservation_status": conservation_status,
            "compliance_status": ComplianceStatus.COMPLIANT if is_compliant else ComplianceStatus.NON_COMPLIANT,
            "requirements": [],
            "restrictions": [],
            "recommendations": []
        }
        
        if not is_compliant:
            compliance_info["restrictions"].append(f"Quantity exceeds limit: {max_allowed} kg maximum")
            compliance_info["requirements"].append("Reduce collection quantity or split into multiple permits")
            compliance_info["recommendations"].append("Consider sustainable harvesting practices")
        else:
            compliance_info["requirements"].append("Follow quantity reporting requirements")
            compliance_info["recommendations"].append("Document actual quantity collected")
        
        return compliance_info
    
    async def _check_regional_restrictions(
        self, 
        species: HerbSpecies, 
        location: Dict[str, float]
    ) -> Dict[str, Any]:
        """Check regional harvesting restrictions."""
        lat, lon = location.get("latitude", 0), location.get("longitude", 0)
        
        # Simulate regional restriction checking
        restricted_regions = species.restricted_regions or []
        
        # Simple region detection (in production, use proper geocoding)
        detected_region = self._detect_region(lat, lon)
        
        is_restricted = any(region.lower() in detected_region.lower() for region in restricted_regions)
        
        compliance_info = {
            "check_type": "regional_restrictions",
            "species": species.common_name,
            "location": location,
            "detected_region": detected_region,
            "restricted_regions": restricted_regions,
            "compliance_status": ComplianceStatus.NON_COMPLIANT if is_restricted else ComplianceStatus.COMPLIANT,
            "requirements": [],
            "restrictions": [],
            "recommendations": []
        }
        
        if is_restricted:
            compliance_info["restrictions"].append(f"Collection restricted in {detected_region}")
            compliance_info["requirements"].append("Seek alternative collection locations")
            compliance_info["recommendations"].append("Contact local forest department for guidance")
        else:
            compliance_info["requirements"].append("Verify local collection permissions")
            compliance_info["recommendations"].append("Respect community collection rights")
        
        return compliance_info
    
    async def _check_permit_requirements(self, species: HerbSpecies) -> Dict[str, Any]:
        """Check permit and licensing requirements."""
        conservation_status = species.conservation_status.value
        
        # Define permit requirements based on conservation status
        permit_required = conservation_status in [
            "critically_endangered", "endangered", "vulnerable"
        ]
        
        compliance_info = {
            "check_type": "permit_requirements",
            "species": species.common_name,
            "conservation_status": conservation_status,
            "permit_required": permit_required,
            "compliance_status": ComplianceStatus.REQUIRES_REVIEW if permit_required else ComplianceStatus.COMPLIANT,
            "requirements": [],
            "restrictions": [],
            "recommendations": []
        }
        
        if permit_required:
            compliance_info["requirements"].extend([
                "Obtain collection permit from State Forest Department",
                "Submit harvesting plan and impact assessment",
                "Provide collector certification/training proof"
            ])
            compliance_info["recommendations"].extend([
                "Apply for permits well in advance",
                "Maintain detailed collection records",
                "Follow up with permit conditions"
            ])
        else:
            compliance_info["requirements"].append("Follow general collection guidelines")
            compliance_info["recommendations"].append("Consider voluntary certification for quality assurance")
        
        return compliance_info
    
    async def _fetch_species_requirements(self, species: str, region: str) -> Dict[str, Any]:
        """Fetch detailed regulatory requirements for a species."""
        # Simulate API delay
        await asyncio.sleep(0.5)
        
        # Get species info from settings
        species_info = settings.AYURVEDIC_SPECIES.get(species.lower(), {})
        
        requirements = {
            "species": species,
            "region": region,
            "regulatory_authorities": [
                "National Medicinal Plants Board (NMPB)",
                "Ministry of AYUSH",
                "State Forest Department"
            ],
            "general_requirements": [
                "Follow Good Agricultural and Collection Practices (GACP)",
                "Maintain collection records",
                "Ensure proper identification of species",
                "Follow sustainable harvesting methods"
            ],
            "quality_standards": settings.QUALITY_STANDARDS,
            "documentation_required": [
                "Collection location coordinates",
                "Collection date and time",
                "Collector identification",
                "Species verification",
                "Quantity collected"
            ],
            "compliance_certificates": [
                "Organic certification (if applicable)",
                "Quality test certificates",
                "Sustainability compliance certificate"
            ]
        }
        
        # Add species-specific requirements
        if species_info:
            conservation_status = species_info.get("conservation_status", "least_concern")
            
            if conservation_status in ["endangered", "critically_endangered"]:
                requirements["special_permits"] = [
                    "Wildlife Protection Act clearance",
                    "CITES permit (if applicable)",
                    "State Forest Department permission"
                ]
            
            if species_info.get("restricted_regions"):
                requirements["regional_restrictions"] = {
                    "restricted_areas": species_info["restricted_regions"],
                    "reason": "Conservation or biodiversity protection"
                }
        
        return requirements
    
    def _detect_region(self, lat: float, lon: float) -> str:
        """Detect Indian region from coordinates (simplified)."""
        # Simplified region detection
        if lat > 28:
            return "Northern India"
        elif lat < 15:
            return "Southern India"
        elif lon < 77:
            return "Western India"
        elif lon > 85:
            return "Eastern India"
        else:
            return "Central India"
    
    def _check_quality_parameter(
        self, 
        parameter: str, 
        value: float, 
        standard: Dict[str, Any]
    ) -> bool:
        """Check if a quality parameter meets standards."""
        if "max" in standard:
            return value <= standard["max"]
        elif "min" in standard:
            return value >= standard["min"]
        elif "range" in standard:
            min_val, max_val = standard["range"]
            return min_val <= value <= max_val
        else:
            return True  # No specific standard defined
    
    def _aggregate_compliance_results(
        self, 
        compliance_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregate individual compliance checks into overall result."""
        total_checks = len(compliance_results)
        compliant_checks = sum(
            1 for result in compliance_results 
            if result.get("compliance_status") == ComplianceStatus.COMPLIANT
        )
        
        non_compliant_checks = sum(
            1 for result in compliance_results 
            if result.get("compliance_status") == ComplianceStatus.NON_COMPLIANT
        )
        
        requires_review_checks = sum(
            1 for result in compliance_results 
            if result.get("compliance_status") == ComplianceStatus.REQUIRES_REVIEW
        )
        
        # Determine overall status
        if non_compliant_checks > 0:
            overall_status = ComplianceStatus.NON_COMPLIANT
        elif requires_review_checks > 0:
            overall_status = ComplianceStatus.REQUIRES_REVIEW
        else:
            overall_status = ComplianceStatus.COMPLIANT
        
        # Collect all requirements and recommendations
        all_requirements = []
        all_restrictions = []
        all_recommendations = []
        
        for result in compliance_results:
            all_requirements.extend(result.get("requirements", []))
            all_restrictions.extend(result.get("restrictions", []))
            all_recommendations.extend(result.get("recommendations", []))
        
        return {
            "overall_status": overall_status,
            "compliance_score": compliant_checks / total_checks if total_checks > 0 else 0,
            "total_checks": total_checks,
            "compliant_checks": compliant_checks,
            "non_compliant_checks": non_compliant_checks,
            "requires_review_checks": requires_review_checks,
            "requirements": list(set(all_requirements)),
            "restrictions": list(set(all_restrictions)),
            "recommendations": list(set(all_recommendations)),
            "last_updated": datetime.now()
        }
    
    def _generate_compliance_summary(self, compliance_result: Dict[str, Any]) -> str:
        """Generate human-readable compliance summary."""
        status = compliance_result.get("overall_status")
        score = compliance_result.get("compliance_score", 0)
        
        if status == ComplianceStatus.COMPLIANT:
            return f"✅ Fully compliant ({score:.0%}) - All requirements met"
        elif status == ComplianceStatus.NON_COMPLIANT:
            non_compliant = compliance_result.get("non_compliant_checks", 0)
            return f"❌ Non-compliant - {non_compliant} violation(s) found"
        else:
            review_needed = compliance_result.get("requires_review_checks", 0)
            return f"⚠️ Requires review - {review_needed} item(s) need attention"
    
    def _generate_quality_summary(self, validation_results: List[Dict[str, Any]]) -> str:
        """Generate quality validation summary."""
        if not validation_results:
            return "No quality parameters validated"
        
        compliant_count = sum(1 for r in validation_results if r["compliant"])
        total_count = len(validation_results)
        
        if compliant_count == total_count:
            return f"✅ All quality parameters meet standards ({total_count}/{total_count})"
        else:
            failed_count = total_count - compliant_count
            return f"❌ Quality issues found - {failed_count} parameter(s) out of specification"