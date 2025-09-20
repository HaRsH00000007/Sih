"""
Main validation coordinator that combines satellite and regulatory validation.
"""
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional

from config.settings import settings
from models.schemas import (
    ValidationRequest, ValidationResult, CollectionEvent, 
    ComplianceStatus, AgentResponse
)
from core.satellite import SatelliteDataService
from core.regulatory import RegulatoryService
from utils.logger import get_logger
from utils.helpers import (
    merge_validation_results, create_compliance_summary,
    calculate_age_from_harvest, is_harvest_recent
)

logger = get_logger("validation")

class ValidationCoordinator:
    """Main coordinator for validation processes."""
    
    def __init__(self):
        self.satellite_service = SatelliteDataService()
        self.regulatory_service = RegulatoryService()
        
    async def validate_collection_event(
        self, 
        validation_request: ValidationRequest
    ) -> ValidationResult:
        """Perform comprehensive validation of a collection event."""
        try:
            collection_event = validation_request.collection_event
            validation_types = validation_request.validation_types
            
            logger.info(f"Starting validation for event: {collection_event.event_id}")
            
            # Initialize result
            result = ValidationResult(
                event_id=collection_event.event_id,
                overall_status=ComplianceStatus.PENDING,
                confidence_score=0.0,
                compliance_summary="Validation in progress..."
            )
            
            # Track all validation tasks
            validation_tasks = []
            
            # Basic event validation
            basic_validation = await self._validate_basic_requirements(collection_event)
            validation_tasks.append(basic_validation)
            
            # Satellite validation
            if "satellite" in validation_types:
                satellite_task = asyncio.create_task(
                    self._perform_satellite_validation(collection_event)
                )
                validation_tasks.append(satellite_task)
            
            # Regulatory validation  
            if "regulatory" in validation_types:
                regulatory_task = asyncio.create_task(
                    self._perform_regulatory_validation(collection_event)
                )
                validation_tasks.append(regulatory_task)
            
            # Quality validation
            if "quality" in validation_types and collection_event.quality_metrics:
                quality_task = asyncio.create_task(
                    self._perform_quality_validation(collection_event)
                )
                validation_tasks.append(quality_task)
            
            # Wait for all validation tasks to complete
            validation_results = await asyncio.gather(*validation_tasks, return_exceptions=True)
            
            # Process results
            successful_results = []
            errors = []
            
            for i, task_result in enumerate(validation_results):
                if isinstance(task_result, Exception):
                    logger.error(f"Validation task {i} failed: {str(task_result)}")
                    errors.append(str(task_result))
                else:
                    successful_results.append(task_result)
            
            # Combine all validation results
            if successful_results:
                final_result = await self._combine_validation_results(
                    collection_event, successful_results, errors
                )
                return final_result
            else:
                # All validations failed
                return ValidationResult(
                    event_id=collection_event.event_id,
                    overall_status=ComplianceStatus.REQUIRES_REVIEW,
                    confidence_score=0.0,
                    compliance_summary="❌ Validation failed due to technical errors",
                    warnings=[f"Validation error: {error}" for error in errors],
                    next_steps=["Retry validation", "Contact technical support"]
                )
            
        except Exception as e:
            logger.error(f"Critical error in validation coordinator: {str(e)}")
            return ValidationResult(
                event_id=validation_request.collection_event.event_id,
                overall_status=ComplianceStatus.REQUIRES_REVIEW,
                confidence_score=0.0,
                compliance_summary="❌ Critical validation error occurred",
                warnings=[f"Critical error: {str(e)}"],
                next_steps=["Retry validation", "Contact technical support"]
            )
    
    async def _validate_basic_requirements(self, collection_event: CollectionEvent) -> Dict[str, Any]:
        """Perform basic validation checks on the collection event."""
        logger.info("Performing basic validation checks")
        
        validation_result = {
            "validation_type": "basic_requirements",
            "status": ComplianceStatus.COMPLIANT,
            "confidence": 1.0,
            "checks": {},
            "issues": [],
            "warnings": [],
            "recommendations": []
        }
        
        checks = validation_result["checks"]
        issues = validation_result["issues"]
        warnings = validation_result["warnings"]
        recommendations = validation_result["recommendations"]
        
        # Check harvest age
        harvest_age = calculate_age_from_harvest(collection_event.timestamp)
        checks["harvest_age_days"] = harvest_age
        checks["harvest_recent"] = is_harvest_recent(collection_event.timestamp)
        
        if not is_harvest_recent(collection_event.timestamp):
            issues.append(f"Harvest is {harvest_age} days old (max allowed: {settings.MAX_HARVEST_AGE_DAYS})")
            validation_result["status"] = ComplianceStatus.NON_COMPLIANT
        elif harvest_age > settings.MAX_HARVEST_AGE_DAYS // 2:
            warnings.append(f"Harvest is {harvest_age} days old - quality may be affected")
        
        # Check coordinates validity
        lat, lon = collection_event.location.latitude, collection_event.location.longitude
        checks["coordinates_valid"] = -90 <= lat <= 90 and -180 <= lon <= 180
        
        if not checks["coordinates_valid"]:
            issues.append("Invalid GPS coordinates provided")
            validation_result["status"] = ComplianceStatus.NON_COMPLIANT
        
        # Check quantity reasonableness
        checks["quantity_reasonable"] = 0.1 <= collection_event.quantity_kg <= 1000
        
        if not checks["quantity_reasonable"]:
            if collection_event.quantity_kg < 0.1:
                warnings.append("Very small quantity collected - verify measurement")
            else:
                issues.append("Unusually large quantity - may require special permits")
                validation_result["status"] = ComplianceStatus.REQUIRES_REVIEW
        
        # Check collector information completeness
        collector = collection_event.collector
        checks["collector_info_complete"] = bool(
            collector.collector_id and 
            collector.name and 
            len(collector.name.strip()) >= 2
        )
        
        if not checks["collector_info_complete"]:
            issues.append("Incomplete collector information")
            validation_result["status"] = ComplianceStatus.NON_COMPLIANT
        
        # Check species information
        species = collection_event.species
        checks["species_info_complete"] = bool(
            species.common_name and 
            species.scientific_name and
            species.conservation_status
        )
        
        if not checks["species_info_complete"]:
            issues.append("Incomplete species information")
            validation_result["status"] = ComplianceStatus.NON_COMPLIANT
        
        # Generate recommendations
        if harvest_age > 1:
            recommendations.append("Process herbs quickly to maintain quality")
        
        if not collector.license_number:
            recommendations.append("Consider obtaining collector certification")
        
        if not collection_event.photos:
            recommendations.append("Include photos for verification purposes")
        
        logger.info(f"Basic validation completed: {validation_result['status']}")
        return validation_result
    
    async def _perform_satellite_validation(self, collection_event: CollectionEvent) -> Dict[str, Any]:
        """Perform satellite-based validation."""
        logger.info("Performing satellite validation")
        
        try:
            # Get satellite validation
            satellite_response = await self.satellite_service.validate_location(
                collection_event.location,
                collection_event.timestamp,
                collection_event.species.common_name
            )
            
            if satellite_response.success:
                satellite_data = satellite_response.data
                return {
                    "validation_type": "satellite",
                    "status": self._interpret_satellite_status(satellite_data),
                    "confidence": satellite_data.get("confidence_score", 0.5),
                    "data": satellite_data,
                    "issues": self._extract_satellite_issues(satellite_data),
                    "warnings": self._extract_satellite_warnings(satellite_data),
                    "recommendations": self._extract_satellite_recommendations(satellite_data)
                }
            else:
                return {
                    "validation_type": "satellite",
                    "status": ComplianceStatus.REQUIRES_REVIEW,
                    "confidence": 0.0,
                    "issues": [f"Satellite validation failed: {satellite_response.error}"],
                    "warnings": ["Could not verify location using satellite data"],
                    "recommendations": ["Retry validation", "Provide additional location verification"]
                }
                
        except Exception as e:
            logger.error(f"Error in satellite validation: {str(e)}")
            return {
                "validation_type": "satellite",
                "status": ComplianceStatus.REQUIRES_REVIEW,
                "confidence": 0.0,
                "issues": [f"Satellite validation error: {str(e)}"],
                "warnings": ["Technical error in satellite validation"],
                "recommendations": ["Retry validation", "Contact technical support"]
            }
    
    async def _perform_regulatory_validation(self, collection_event: CollectionEvent) -> Dict[str, Any]:
        """Perform regulatory compliance validation."""
        logger.info("Performing regulatory validation")
        
        try:
            # Check species compliance
            compliance_response = await self.regulatory_service.check_species_compliance(
                collection_event.species,
                collection_event.timestamp,
                {
                    "latitude": collection_event.location.latitude,
                    "longitude": collection_event.location.longitude
                },
                collection_event.quantity_kg
            )
            
            if compliance_response.success:
                compliance_data = compliance_response.data
                overall_compliance = compliance_data.get("overall_compliance", {})
                
                return {
                    "validation_type": "regulatory",
                    "status": overall_compliance.get("overall_status", ComplianceStatus.PENDING),
                    "confidence": overall_compliance.get("compliance_score", 0.5),
                    "data": compliance_data,
                    "issues": self._extract_compliance_issues(overall_compliance),
                    "warnings": self._extract_compliance_warnings(overall_compliance),
                    "recommendations": overall_compliance.get("recommendations", [])
                }
            else:
                return {
                    "validation_type": "regulatory",
                    "status": ComplianceStatus.REQUIRES_REVIEW,
                    "confidence": 0.0,
                    "issues": [f"Regulatory validation failed: {compliance_response.error}"],
                    "warnings": ["Could not verify regulatory compliance"],
                    "recommendations": ["Retry validation", "Consult regulatory guidelines manually"]
                }
                
        except Exception as e:
            logger.error(f"Error in regulatory validation: {str(e)}")
            return {
                "validation_type": "regulatory",
                "status": ComplianceStatus.REQUIRES_REVIEW,
                "confidence": 0.0,
                "issues": [f"Regulatory validation error: {str(e)}"],
                "warnings": ["Technical error in regulatory validation"],
                "recommendations": ["Retry validation", "Contact regulatory expert"]
            }
    
    async def _perform_quality_validation(self, collection_event: CollectionEvent) -> Dict[str, Any]:
        """Perform quality standards validation."""
        logger.info("Performing quality validation")
        
        try:
            if not collection_event.quality_metrics:
                return {
                    "validation_type": "quality",
                    "status": ComplianceStatus.REQUIRES_REVIEW,
                    "confidence": 0.0,
                    "issues": ["No quality metrics provided"],
                    "warnings": ["Quality cannot be assessed without measurements"],
                    "recommendations": ["Conduct quality tests", "Provide quality measurements"]
                }
            
            # Convert quality metrics to dict
            quality_dict = {}
            if collection_event.quality_metrics.moisture_content is not None:
                quality_dict["moisture_content"] = collection_event.quality_metrics.moisture_content
            if collection_event.quality_metrics.ash_content is not None:
                quality_dict["ash_content"] = collection_event.quality_metrics.ash_content
            
            # Validate against standards
            quality_response = await self.regulatory_service.validate_quality_standards(
                collection_event.species.common_name,
                quality_dict
            )
            
            if quality_response.success:
                quality_data = quality_response.data
                overall_compliant = quality_data.get("overall_compliant", False)
                
                return {
                    "validation_type": "quality",
                    "status": ComplianceStatus.COMPLIANT if overall_compliant else ComplianceStatus.NON_COMPLIANT,
                    "confidence": quality_data.get("compliance_rate", 0.5),
                    "data": quality_data,
                    "issues": self._extract_quality_issues(quality_data),
                    "warnings": self._extract_quality_warnings(quality_data),
                    "recommendations": ["Maintain quality standards", "Document quality measurements"]
                }
            else:
                return {
                    "validation_type": "quality",
                    "status": ComplianceStatus.REQUIRES_REVIEW,
                    "confidence": 0.0,
                    "issues": [f"Quality validation failed: {quality_response.error}"],
                    "warnings": ["Could not validate quality standards"],
                    "recommendations": ["Retry validation", "Review quality measurements"]
                }
                
        except Exception as e:
            logger.error(f"Error in quality validation: {str(e)}")
            return {
                "validation_type": "quality",
                "status": ComplianceStatus.REQUIRES_REVIEW,
                "confidence": 0.0,
                "issues": [f"Quality validation error: {str(e)}"],
                "warnings": ["Technical error in quality validation"],
                "recommendations": ["Retry validation", "Review quality data"]
            }
    
    async def _combine_validation_results(
        self, 
        collection_event: CollectionEvent,
        validation_results: List[Dict[str, Any]],
        errors: List[str]
    ) -> ValidationResult:
        """Combine all validation results into final result."""
        logger.info("Combining validation results")
        
        # Aggregate all issues, warnings, recommendations
        all_issues = []
        all_warnings = []
        all_recommendations = []
        data_sources = []
        
        # Track validation statuses and confidence scores
        statuses = []
        confidence_scores = []
        
        for result in validation_results:
            validation_type = result.get("validation_type", "unknown")
            status = result.get("status", ComplianceStatus.PENDING)
            confidence = result.get("confidence", 0.0)
            
            statuses.append(status)
            confidence_scores.append(confidence)
            data_sources.append(validation_type)
            
            # Collect feedback
            all_issues.extend(result.get("issues", []))
            all_warnings.extend(result.get("warnings", []))
            all_recommendations.extend(result.get("recommendations", []))
        
        # Add any errors
        if errors:
            all_warnings.extend([f"Validation error: {error}" for error in errors])
        
        # Determine overall status
        overall_status = self._determine_overall_status(statuses)
        
        # Calculate overall confidence
        overall_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        # Apply confidence penalty for errors
        if errors:
            overall_confidence *= max(0.5, 1.0 - len(errors) * 0.2)
        
        # Generate compliance summary
        compliance_summary = create_compliance_summary(
            [issue for issue in all_issues if "violation" in issue.lower()],
            all_warnings
        )
        
        # Generate next steps
        next_steps = self._generate_next_steps(overall_status, all_issues, validation_results)
        
        # Prepare detailed data
        validation_data = {
            "validation_breakdown": validation_results,
            "total_validations": len(validation_results),
            "successful_validations": len([r for r in validation_results if r.get("status") != ComplianceStatus.REQUIRES_REVIEW]),
            "confidence_breakdown": dict(zip(data_sources, confidence_scores))
        }
        
        return ValidationResult(
            event_id=collection_event.event_id,
            overall_status=overall_status,
            confidence_score=round(overall_confidence, 3),
            compliance_summary=compliance_summary,
            recommendations=list(set(all_recommendations)),
            warnings=list(set(all_warnings)),
            next_steps=next_steps,
            data_sources_used=data_sources,
            validation_duration_seconds=None  # Could track this if needed
        )
    
    def _determine_overall_status(self, statuses: List[ComplianceStatus]) -> ComplianceStatus:
        """Determine overall compliance status from individual statuses."""
        if not statuses:
            return ComplianceStatus.PENDING
        
        # If any are non-compliant, overall is non-compliant
        if ComplianceStatus.NON_COMPLIANT in statuses:
            return ComplianceStatus.NON_COMPLIANT
        
        # If any require review, overall requires review
        if ComplianceStatus.REQUIRES_REVIEW in statuses:
            return ComplianceStatus.REQUIRES_REVIEW
        
        # If all are compliant or pending, overall is compliant
        if all(status in [ComplianceStatus.COMPLIANT, ComplianceStatus.PENDING] for status in statuses):
            return ComplianceStatus.COMPLIANT
        
        return ComplianceStatus.REQUIRES_REVIEW
    
    def _generate_next_steps(
        self, 
        overall_status: ComplianceStatus,
        issues: List[str],
        validation_results: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate appropriate next steps based on validation results."""
        next_steps = []
        
        if overall_status == ComplianceStatus.NON_COMPLIANT:
            next_steps.append("Address compliance violations before proceeding")
            if any("permit" in issue.lower() for issue in issues):
                next_steps.append("Obtain required permits and licenses")
            if any("season" in issue.lower() for issue in issues):
                next_steps.append("Wait for appropriate harvesting season")
            if any("quantity" in issue.lower() for issue in issues):
                next_steps.append("Reduce collection quantity or split into multiple permits")
        
        elif overall_status == ComplianceStatus.REQUIRES_REVIEW:
            next_steps.append("Review flagged items with regulatory expert")
            if any("satellite" in str(result).lower() for result in validation_results):
                next_steps.append("Verify location data and satellite connectivity")
            next_steps.append("Consider additional documentation or verification")
        
        else:  # COMPLIANT
            next_steps.append("Proceed with collection following best practices")
            next_steps.append("Maintain detailed records of collection process")
            next_steps.append("Conduct quality testing after processing")
        
        # Add general next steps
        next_steps.append("Update traceability records in blockchain")
        
        return next_steps
    
    # Helper methods for extracting information from validation results
    
    def _interpret_satellite_status(self, satellite_data: Dict[str, Any]) -> ComplianceStatus:
        """Interpret satellite validation data to determine compliance status."""
        validation_score = satellite_data.get("confidence_score", 0.5)
        anomalies = satellite_data.get("satellite_data", {}).get("anomalies_detected", [])
        
        if validation_score >= 0.8 and not anomalies:
            return ComplianceStatus.COMPLIANT
        elif validation_score >= 0.6:
            return ComplianceStatus.REQUIRES_REVIEW
        else:
            return ComplianceStatus.NON_COMPLIANT
    
    def _extract_satellite_issues(self, satellite_data: Dict[str, Any]) -> List[str]:
        """Extract issues from satellite validation data."""
        issues = []
        sat_data = satellite_data.get("satellite_data", {})
        
        # Check for critical anomalies
        anomalies = sat_data.get("anomalies_detected", [])
        for anomaly in anomalies:
            if "barren" in anomaly.lower() or "unsuitable" in anomaly.lower():
                issues.append(f"Location issue: {anomaly}")
        
        # Check validation score
        validation_score = satellite_data.get("confidence_score", 0.5)
        if validation_score < 0.5:
            issues.append("Low satellite validation confidence - location may be inappropriate")
        
        return issues
    
    def _extract_satellite_warnings(self, satellite_data: Dict[str, Any]) -> List[str]:
        """Extract warnings from satellite validation data."""
        warnings = []
        sat_data = satellite_data.get("satellite_data", {})
        
        # Cloud cover warnings
        cloud_cover = sat_data.get("cloud_cover", 0)
        if cloud_cover > 70:
            warnings.append(f"High cloud cover ({cloud_cover}%) may affect validation accuracy")
        
        # Vegetation index warnings
        vegetation_index = sat_data.get("vegetation_index", 0.5)
        if vegetation_index < 0.4:
            warnings.append("Low vegetation index detected - verify site suitability")
        
        # General anomaly warnings
        anomalies = sat_data.get("anomalies_detected", [])
        for anomaly in anomalies:
            if "high" in anomaly.lower() or "unusual" in anomaly.lower():
                warnings.append(f"Satellite observation: {anomaly}")
        
        return warnings
    
    def _extract_satellite_recommendations(self, satellite_data: Dict[str, Any]) -> List[str]:
        """Extract recommendations from satellite validation data."""
        recommendations = []
        sat_data = satellite_data.get("satellite_data", {})
        
        # Vegetation health recommendations
        vegetation_index = sat_data.get("vegetation_index", 0.5)
        if vegetation_index > 0.7:
            recommendations.append("Good vegetation health - optimal for collection")
        elif vegetation_index < 0.4:
            recommendations.append("Consider alternative locations with better vegetation")
        
        # Seasonal recommendations
        land_use = sat_data.get("land_use_type", "")
        if land_use == "agricultural":
            recommendations.append("Verify organic cultivation practices if applicable")
        elif land_use == "forest":
            recommendations.append("Follow sustainable wild harvesting practices")
        
        return recommendations
    
    def _extract_compliance_issues(self, compliance_data: Dict[str, Any]) -> List[str]:
        """Extract issues from regulatory compliance data."""
        issues = []
        
        restrictions = compliance_data.get("restrictions", [])
        for restriction in restrictions:
            issues.append(f"Compliance violation: {restriction}")
        
        if compliance_data.get("non_compliant_checks", 0) > 0:
            issues.append("One or more regulatory requirements not met")
        
        return issues
    
    def _extract_compliance_warnings(self, compliance_data: Dict[str, Any]) -> List[str]:
        """Extract warnings from regulatory compliance data."""
        warnings = []
        
        if compliance_data.get("requires_review_checks", 0) > 0:
            warnings.append("Some requirements need additional review")
        
        # Check compliance score
        compliance_score = compliance_data.get("compliance_score", 0.0)
        if 0.5 <= compliance_score < 0.8:
            warnings.append("Moderate compliance score - review all requirements carefully")
        
        return warnings
    
    def _extract_quality_issues(self, quality_data: Dict[str, Any]) -> List[str]:
        """Extract issues from quality validation data."""
        issues = []
        
        if not quality_data.get("overall_compliant", True):
            failed_params = [
                r["parameter"] for r in quality_data.get("parameter_results", [])
                if not r.get("compliant", True)
            ]
            if failed_params:
                issues.append(f"Quality parameters failed: {', '.join(failed_params)}")
        
        return issues
    
    def _extract_quality_warnings(self, quality_data: Dict[str, Any]) -> List[str]:
        """Extract warnings from quality validation data."""
        warnings = []
        
        compliance_rate = quality_data.get("compliance_rate", 1.0)
        if 0.7 <= compliance_rate < 1.0:
            warnings.append("Some quality parameters are borderline - monitor closely")
        
        return warnings