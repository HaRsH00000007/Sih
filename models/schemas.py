# Pydantic or dataclass models for input/output validation
"""
Pydantic models and schemas for VrukshaChain data validation.
"""
from datetime import datetime, date
from typing import List, Dict, Optional, Any, Literal
from pydantic import BaseModel, Field, validator, EmailStr
from enum import Enum

class ConservationStatus(str, Enum):
    """Conservation status enumeration."""
    EXTINCT = "extinct"
    CRITICALLY_ENDANGERED = "critically_endangered" 
    ENDANGERED = "endangered"
    VULNERABLE = "vulnerable"
    NEAR_THREATENED = "near_threatened"
    LEAST_CONCERN = "least_concern"
    DATA_DEFICIENT = "data_deficient"

class HarvestSeason(str, Enum):
    """Harvest season enumeration."""
    SUMMER = "summer"
    MONSOON = "monsoon"
    POST_MONSOON = "post_monsoon"
    WINTER = "winter"
    SPRING = "spring"

class ComplianceStatus(str, Enum):
    """Compliance status enumeration."""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PENDING = "pending"
    REQUIRES_REVIEW = "requires_review"

class Coordinates(BaseModel):
    """Geographic coordinates model."""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")
    accuracy: Optional[float] = Field(None, description="GPS accuracy in meters")
    altitude: Optional[float] = Field(None, description="Altitude in meters")

class CollectorInfo(BaseModel):
    """Information about the herb collector."""
    collector_id: str = Field(..., description="Unique collector identifier")
    name: str = Field(..., min_length=2, max_length=100, description="Collector name")
    license_number: Optional[str] = Field(None, description="Collection license number")
    experience_years: Optional[int] = Field(None, ge=0, description="Years of experience")
    contact_info: Optional[str] = Field(None, description="Contact information")

class HerbSpecies(BaseModel):
    """Ayurvedic herb species information."""
    common_name: str = Field(..., description="Common name of the herb")
    scientific_name: str = Field(..., description="Scientific name")
    local_names: Optional[List[str]] = Field(default_factory=list, description="Local names")
    conservation_status: ConservationStatus = Field(..., description="Conservation status")
    harvest_seasons: List[HarvestSeason] = Field(..., description="Allowed harvest seasons")
    restricted_regions: Optional[List[str]] = Field(default_factory=list, description="Restricted harvest regions")

class QualityMetrics(BaseModel):
    """Quality assessment metrics."""
    moisture_content: Optional[float] = Field(None, ge=0, le=100, description="Moisture percentage")
    ash_content: Optional[float] = Field(None, ge=0, le=100, description="Ash content percentage")
    visual_quality_score: Optional[int] = Field(None, ge=1, le=10, description="Visual quality (1-10)")
    contamination_present: Optional[bool] = Field(None, description="Contamination detected")
    notes: Optional[str] = Field(None, description="Additional quality notes")

class SatelliteData(BaseModel):
    """Satellite validation data."""
    image_date: datetime = Field(..., description="Date of satellite image")
    cloud_cover: Optional[float] = Field(None, ge=0, le=100, description="Cloud cover percentage")
    vegetation_index: Optional[float] = Field(None, description="NDVI or similar vegetation index")
    land_use_type: Optional[str] = Field(None, description="Detected land use type")
    validation_score: float = Field(..., ge=0, le=1, description="Validation confidence score")
    anomalies_detected: Optional[List[str]] = Field(default_factory=list, description="Detected anomalies")

class RegulatoryInfo(BaseModel):
    """Regulatory compliance information."""
    authority: str = Field(..., description="Regulatory authority")
    regulation_id: Optional[str] = Field(None, description="Specific regulation ID")
    compliance_status: ComplianceStatus = Field(..., description="Compliance status")
    requirements: List[str] = Field(..., description="Specific requirements")
    violation_details: Optional[List[str]] = Field(default_factory=list, description="Violation details if any")
    last_updated: datetime = Field(..., description="Last regulation update")

class CollectionEvent(BaseModel):
    """Main collection event model."""
    event_id: str = Field(..., description="Unique event identifier")
    timestamp: datetime = Field(default_factory=datetime.now, description="Collection timestamp")
    collector: CollectorInfo = Field(..., description="Collector information")
    location: Coordinates = Field(..., description="Collection coordinates")
    species: HerbSpecies = Field(..., description="Herb species information")
    quantity_kg: float = Field(..., gt=0, description="Quantity collected in kg")
    harvest_method: Optional[str] = Field(None, description="Harvesting method used")
    quality_metrics: Optional[QualityMetrics] = Field(None, description="Quality assessment")
    photos: Optional[List[str]] = Field(default_factory=list, description="Photo URLs/paths")
    weather_conditions: Optional[str] = Field(None, description="Weather during collection")
    notes: Optional[str] = Field(None, description="Additional notes")

    @validator('timestamp')
    def validate_timestamp(cls, v):
        """Ensure timestamp is not in the future."""
        if v > datetime.now():
            raise ValueError('Collection timestamp cannot be in the future')
        return v

class ValidationRequest(BaseModel):
    """Validation request model."""
    collection_event: CollectionEvent = Field(..., description="Collection event to validate")
    validation_types: List[str] = Field(
        default=["satellite", "regulatory", "quality"],
        description="Types of validation to perform"
    )
    priority: Literal["low", "normal", "high", "urgent"] = Field(
        default="normal",
        description="Validation priority"
    )

class ValidationResult(BaseModel):
    """Comprehensive validation result."""
    event_id: str = Field(..., description="Collection event ID")
    validation_timestamp: datetime = Field(default_factory=datetime.now, description="Validation timestamp")
    overall_status: ComplianceStatus = Field(..., description="Overall compliance status")
    confidence_score: float = Field(..., ge=0, le=1, description="Overall confidence score")
    
    # Individual validation results
    satellite_validation: Optional[SatelliteData] = Field(None, description="Satellite validation results")
    regulatory_compliance: List[RegulatoryInfo] = Field(default_factory=list, description="Regulatory compliance results")
    quality_assessment: Optional[QualityMetrics] = Field(None, description="Quality assessment results")
    
    # Detailed feedback
    compliance_summary: str = Field(..., description="Human-readable compliance summary")
    recommendations: List[str] = Field(default_factory=list, description="Improvement recommendations")
    warnings: List[str] = Field(default_factory=list, description="Warnings and alerts")
    next_steps: List[str] = Field(default_factory=list, description="Suggested next steps")
    
    # Additional metadata
    validation_duration_seconds: Optional[float] = Field(None, description="Time taken for validation")
    data_sources_used: List[str] = Field(default_factory=list, description="Data sources consulted")

class AgentResponse(BaseModel):
    """Agent response model for API calls."""
    success: bool = Field(..., description="Whether the request was successful")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    message: str = Field(..., description="Response message")
    error: Optional[str] = Field(None, description="Error message if any")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    source: str = Field(..., description="Source agent/service")

class ProcessingStep(BaseModel):
    """Processing step in the supply chain."""
    step_id: str = Field(..., description="Unique step identifier")
    event_id: str = Field(..., description="Related collection event ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="Processing timestamp")
    processor_id: str = Field(..., description="Processor identifier")
    step_type: str = Field(..., description="Type of processing step")
    input_quantity: float = Field(..., gt=0, description="Input quantity")
    output_quantity: float = Field(..., gt=0, description="Output quantity")
    quality_parameters: Optional[QualityMetrics] = Field(None, description="Quality after processing")
    notes: Optional[str] = Field(None, description="Processing notes")

class QualityTest(BaseModel):
    """Laboratory quality test results."""
    test_id: str = Field(..., description="Unique test identifier")
    event_id: str = Field(..., description="Related collection event ID")
    lab_name: str = Field(..., description="Laboratory name")
    test_date: datetime = Field(..., description="Test date")
    test_type: str = Field(..., description="Type of test performed")
    parameters_tested: List[str] = Field(..., description="Parameters tested")
    results: Dict[str, float] = Field(..., description="Test results")
    pass_fail_status: ComplianceStatus = Field(..., description="Pass/fail status")
    certificate_url: Optional[str] = Field(None, description="Certificate URL")
    notes: Optional[str] = Field(None, description="Test notes")