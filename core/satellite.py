"""
Satellite data fetching and validation logic.
"""
import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import random

from config.settings import settings
from models.schemas import SatelliteData, AgentResponse, Coordinates
from utils.logger import get_logger
from utils.helpers import validate_coordinates, calculate_distance

logger = get_logger("satellite")

class SatelliteDataService:
    """Service for fetching and processing satellite data."""
    
    def __init__(self):
        self.timeout = settings.SATELLITE_API_TIMEOUT
        self.cache_hours = settings.SATELLITE_CACHE_HOURS
        self._cache = {}
    
    async def validate_location(
        self, 
        coordinates: Coordinates, 
        timestamp: datetime,
        species: str = None
    ) -> AgentResponse:
        """Validate collection location using satellite data."""
        try:
            if not validate_coordinates(coordinates.latitude, coordinates.longitude):
                return AgentResponse(
                    success=False,
                    message="Invalid coordinates provided",
                    error="Coordinates out of valid range",
                    source="satellite_service"
                )
            
            logger.info(f"Validating location: {coordinates.latitude}, {coordinates.longitude}")
            
            # For demo purposes, we'll simulate satellite validation
            # In production, this would call actual APIs like Sentinel Hub, NASA Earth, etc.
            satellite_data = await self._fetch_satellite_imagery(coordinates, timestamp)
            
            if satellite_data:
                validation_result = self._analyze_satellite_data(
                    satellite_data, coordinates, timestamp, species
                )
                
                return AgentResponse(
                    success=True,
                    data=validation_result,
                    message="Satellite validation completed",
                    source="satellite_service"
                )
            else:
                return AgentResponse(
                    success=False,
                    message="Could not retrieve satellite data",
                    error="No satellite imagery available for location and date",
                    source="satellite_service"
                )
                
        except Exception as e:
            logger.error(f"Error in satellite validation: {str(e)}")
            return AgentResponse(
                success=False,
                message="Satellite validation failed",
                error=str(e),
                source="satellite_service"
            )
    
    async def get_vegetation_health(
        self, 
        coordinates: Coordinates, 
        date_range: int = 30
    ) -> AgentResponse:
        """Get vegetation health metrics for a location."""
        try:
            logger.info(f"Fetching vegetation health for: {coordinates.latitude}, {coordinates.longitude}")
            
            # Simulate vegetation health analysis
            health_data = await self._analyze_vegetation_health(coordinates, date_range)
            
            return AgentResponse(
                success=True,
                data=health_data,
                message="Vegetation health analysis completed",
                source="satellite_service"
            )
            
        except Exception as e:
            logger.error(f"Error getting vegetation health: {str(e)}")
            return AgentResponse(
                success=False,
                message="Failed to analyze vegetation health",
                error=str(e),
                source="satellite_service"
            )
    
    async def check_land_use_compliance(
        self, 
        coordinates: Coordinates, 
        expected_land_use: str = "agricultural"
    ) -> AgentResponse:
        """Check if land use is appropriate for herb collection."""
        try:
            logger.info(f"Checking land use compliance for: {coordinates.latitude}, {coordinates.longitude}")
            
            # Simulate land use analysis
            land_use_data = await self._analyze_land_use(coordinates, expected_land_use)
            
            return AgentResponse(
                success=True,
                data=land_use_data,
                message="Land use analysis completed",
                source="satellite_service"
            )
            
        except Exception as e:
            logger.error(f"Error checking land use: {str(e)}")
            return AgentResponse(
                success=False,
                message="Failed to analyze land use",
                error=str(e),
                source="satellite_service"
            )
    
    async def _fetch_satellite_imagery(
        self, 
        coordinates: Coordinates, 
        timestamp: datetime
    ) -> Optional[Dict[str, Any]]:
        """Fetch satellite imagery data (simulated for demo)."""
        # Cache key
        cache_key = f"{coordinates.latitude:.4f}_{coordinates.longitude:.4f}_{timestamp.date()}"
        
        # Check cache
        if cache_key in self._cache:
            cache_time, data = self._cache[cache_key]
            if datetime.now() - cache_time < timedelta(hours=self.cache_hours):
                logger.info("Using cached satellite data")
                return data
        
        # Simulate API call delay
        await asyncio.sleep(1)
        
        # Simulate satellite data based on location characteristics
        satellite_data = self._simulate_satellite_data(coordinates, timestamp)
        
        # Cache result
        self._cache[cache_key] = (datetime.now(), satellite_data)
        
        return satellite_data
    
    def _simulate_satellite_data(
        self, 
        coordinates: Coordinates, 
        timestamp: datetime
    ) -> Dict[str, Any]:
        """Simulate realistic satellite data for demonstration."""
        # Base simulation on location and season
        lat, lon = coordinates.latitude, coordinates.longitude
        
        # Simulate based on Indian geography
        is_northern = lat > 25
        is_coastal = (lon < 75 and lat < 20) or (lon > 85 and lat < 25)
        is_monsoon_season = timestamp.month in [6, 7, 8, 9]
        is_winter = timestamp.month in [11, 12, 1, 2]
        
        # Generate realistic values
        cloud_cover = random.uniform(10, 90) if is_monsoon_season else random.uniform(5, 40)
        
        # NDVI (vegetation index) - higher in monsoon, lower in winter
        if is_monsoon_season:
            vegetation_index = random.uniform(0.6, 0.9)
        elif is_winter:
            vegetation_index = random.uniform(0.3, 0.6)
        else:
            vegetation_index = random.uniform(0.4, 0.7)
        
        # Land use simulation
        land_use_options = ["agricultural", "forest", "grassland", "mixed_vegetation", "barren"]
        if is_northern:
            land_use_type = random.choice(["agricultural", "mixed_vegetation", "grassland"])
        else:
            land_use_type = random.choice(["forest", "agricultural", "mixed_vegetation"])
        
        # Validation score based on conditions
        validation_score = 0.8
        if cloud_cover > 70:
            validation_score -= 0.2
        if vegetation_index < 0.4:
            validation_score -= 0.1
        if land_use_type == "barren":
            validation_score -= 0.3
        
        validation_score = max(0.1, min(1.0, validation_score))
        
        return {
            "image_date": timestamp,
            "cloud_cover": round(cloud_cover, 2),
            "vegetation_index": round(vegetation_index, 3),
            "land_use_type": land_use_type,
            "validation_score": round(validation_score, 3),
            "anomalies_detected": self._detect_anomalies(vegetation_index, cloud_cover, land_use_type),
            "metadata": {
                "source": "simulated_sentinel",
                "resolution_meters": 10,
                "bands_analyzed": ["B4", "B8", "B11"]
            }
        }
    
    def _detect_anomalies(
        self, 
        vegetation_index: float, 
        cloud_cover: float, 
        land_use_type: str
    ) -> List[str]:
        """Detect potential anomalies in satellite data."""
        anomalies = []
        
        if vegetation_index < 0.3:
            anomalies.append("Low vegetation cover detected")
        
        if cloud_cover > 80:
            anomalies.append("High cloud cover affecting image quality")
        
        if land_use_type == "barren":
            anomalies.append("Barren land detected - unsuitable for herb collection")
        
        if vegetation_index > 0.8 and land_use_type == "agricultural":
            anomalies.append("Unusually high vegetation - possible irrigation or fertilization")
        
        return anomalies
    
    def _analyze_satellite_data(
        self, 
        satellite_data: Dict[str, Any], 
        coordinates: Coordinates, 
        timestamp: datetime,
        species: str = None
    ) -> Dict[str, Any]:
        """Analyze satellite data for compliance validation."""
        analysis = {
            "coordinates": {
                "latitude": coordinates.latitude,
                "longitude": coordinates.longitude
            },
            "satellite_data": satellite_data,
            "compliance_checks": {},
            "validation_summary": "",
            "confidence_score": satellite_data.get("validation_score", 0.5)
        }
        
        # Perform compliance checks
        checks = analysis["compliance_checks"]
        
        # Vegetation health check
        vegetation_index = satellite_data.get("vegetation_index", 0.5)
        if vegetation_index >= 0.6:
            checks["vegetation_health"] = "good"
        elif vegetation_index >= 0.4:
            checks["vegetation_health"] = "moderate"
        else:
            checks["vegetation_health"] = "poor"
        
        # Land use appropriateness
        land_use = satellite_data.get("land_use_type", "unknown")
        appropriate_land_uses = ["agricultural", "forest", "mixed_vegetation", "grassland"]
        checks["land_use_appropriate"] = land_use in appropriate_land_uses
        
        # Image quality check
        cloud_cover = satellite_data.get("cloud_cover", 0)
        checks["image_quality"] = "good" if cloud_cover < 30 else "moderate" if cloud_cover < 70 else "poor"
        
        # Seasonal appropriateness (if species is known)
        if species:
            checks["seasonal_compliance"] = self._check_seasonal_compliance(timestamp, species)
        
        # Generate validation summary
        analysis["validation_summary"] = self._generate_validation_summary(checks, satellite_data)
        
        return analysis
    
    def _check_seasonal_compliance(self, timestamp: datetime, species: str) -> str:
        """Check if collection timing is appropriate for species."""
        species_info = settings.AYURVEDIC_SPECIES.get(species.lower())
        if not species_info:
            return "unknown"
        
        # Determine current season
        month = timestamp.month
        if month in [12, 1, 2]:
            current_season = "winter"
        elif month in [3, 4, 5]:
            current_season = "spring"
        elif month in [6, 7, 8]:
            current_season = "monsoon"
        else:
            current_season = "post_monsoon"
        
        allowed_seasons = species_info.get("harvest_season", [])
        return "compliant" if current_season in allowed_seasons else "non_compliant"
    
    def _generate_validation_summary(
        self, 
        checks: Dict[str, Any], 
        satellite_data: Dict[str, Any]
    ) -> str:
        """Generate human-readable validation summary."""
        summary_parts = []
        
        # Vegetation health
        veg_health = checks.get("vegetation_health", "unknown")
        if veg_health == "good":
            summary_parts.append("✅ Good vegetation health detected")
        elif veg_health == "moderate":
            summary_parts.append("⚠️ Moderate vegetation health")
        else:
            summary_parts.append("❌ Poor vegetation health - may indicate unsuitable conditions")
        
        # Land use
        if checks.get("land_use_appropriate", False):
            land_use = satellite_data.get("land_use_type", "unknown")
            summary_parts.append(f"✅ Appropriate land use: {land_use}")
        else:
            summary_parts.append("❌ Inappropriate land use for herb collection")
        
        # Image quality
        quality = checks.get("image_quality", "unknown")
        if quality == "good":
            summary_parts.append("✅ Clear satellite imagery")
        elif quality == "moderate":
            summary_parts.append("⚠️ Moderate image quality due to cloud cover")
        else:
            summary_parts.append("❌ Poor image quality - high cloud cover")
        
        # Seasonal compliance
        seasonal = checks.get("seasonal_compliance")
        if seasonal == "compliant":
            summary_parts.append("✅ Collection timing appropriate for species")
        elif seasonal == "non_compliant":
            summary_parts.append("❌ Collection timing not optimal for species")
        
        # Anomalies
        anomalies = satellite_data.get("anomalies_detected", [])
        if anomalies:
            summary_parts.append(f"⚠️ {len(anomalies)} anomaly(ies) detected")
        
        return "; ".join(summary_parts)
    
    async def _analyze_vegetation_health(
        self, 
        coordinates: Coordinates, 
        date_range: int
    ) -> Dict[str, Any]:
        """Analyze vegetation health over time period."""
        # Simulate vegetation health analysis
        await asyncio.sleep(0.5)
        
        # Generate time series data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=date_range)
        
        health_data = {
            "location": {
                "latitude": coordinates.latitude,
                "longitude": coordinates.longitude
            },
            "date_range": {
                "start": start_date,
                "end": end_date
            },
            "metrics": {
                "average_ndvi": round(random.uniform(0.4, 0.8), 3),
                "trend": random.choice(["improving", "stable", "declining"]),
                "seasonal_pattern": "normal",
                "stress_indicators": []
            },
            "time_series": []
        }
        
        # Generate sample time series
        for i in range(0, date_range, 7):  # Weekly data points
            date = start_date + timedelta(days=i)
            ndvi = random.uniform(0.3, 0.9)
            health_data["time_series"].append({
                "date": date,
                "ndvi": round(ndvi, 3),
                "moisture_stress": random.choice([True, False]),
                "cloud_cover": round(random.uniform(10, 80), 1)
            })
        
        # Add stress indicators
        avg_ndvi = health_data["metrics"]["average_ndvi"]
        if avg_ndvi < 0.4:
            health_data["metrics"]["stress_indicators"].append("Low vegetation vigor")
        if random.random() < 0.3:
            health_data["metrics"]["stress_indicators"].append("Possible drought stress")
        
        return health_data
    
    async def _analyze_land_use(
        self, 
        coordinates: Coordinates, 
        expected_land_use: str
    ) -> Dict[str, Any]:
        """Analyze land use patterns around collection site."""
        await asyncio.sleep(0.5)
        
        # Simulate land use analysis
        possible_land_uses = [
            "agricultural", "forest", "grassland", "mixed_vegetation", 
            "urban", "water_body", "barren", "wetland"
        ]
        
        # Determine actual land use based on coordinates and region
        lat, lon = coordinates.latitude, coordinates.longitude
        
        # Simple heuristic based on Indian geography
        if lat > 28:  # Northern regions
            detected_land_use = random.choice(["agricultural", "mixed_vegetation", "grassland"])
        elif lat < 15:  # Southern regions
            detected_land_use = random.choice(["forest", "agricultural", "mixed_vegetation"])
        else:  # Central regions
            detected_land_use = random.choice(["agricultural", "forest", "grassland"])
        
        # Calculate compliance score
        compliance_score = 0.9 if detected_land_use == expected_land_use else 0.6
        
        # Add some randomness for realism
        if random.random() < 0.2:  # 20% chance of different land use
            detected_land_use = random.choice(possible_land_uses)
            compliance_score = 0.9 if detected_land_use == expected_land_use else 0.4
        
        land_use_data = {
            "location": {
                "latitude": coordinates.latitude,
                "longitude": coordinates.longitude
            },
            "detected_land_use": detected_land_use,
            "expected_land_use": expected_land_use,
            "compliance_score": compliance_score,
            "confidence": random.uniform(0.7, 0.95),
            "surrounding_area": {
                "primary_land_use": detected_land_use,
                "secondary_uses": random.sample(possible_land_uses, 2),
                "fragmentation_index": random.uniform(0.2, 0.8)
            },
            "suitability_assessment": {
                "suitable_for_collection": detected_land_use in [
                    "agricultural", "forest", "mixed_vegetation", "grassland"
                ],
                "risk_factors": [],
                "recommendations": []
            }
        }
        
        # Add risk factors and recommendations
        suitability = land_use_data["suitability_assessment"]
        
        if detected_land_use == "urban":
            suitability["risk_factors"].append("Urban contamination risk")
            suitability["recommendations"].append("Avoid collection in urban areas")
        
        if detected_land_use == "barren":
            suitability["risk_factors"].append("Poor soil quality")
            suitability["recommendations"].append("Seek areas with better vegetation cover")
        
        if detected_land_use == "water_body":
            suitability["risk_factors"].append("Waterlogged conditions")
            suitability["recommendations"].append("Ensure proper drainage for herb quality")
        
        if compliance_score < 0.7:
            suitability["recommendations"].append("Verify land use permits and suitability")
        
        return land_use_data