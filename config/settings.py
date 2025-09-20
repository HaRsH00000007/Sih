"""
Central configuration for VrukshaChain application.
"""
import os
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    """Application settings and configuration."""
    
    # Application Info
    APP_NAME: str = os.getenv("APP_NAME", "VrukshaChain")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # API Keys
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    SERPER_API_KEY: str = os.getenv("SERPER_API_KEY", "")
    
    # API Endpoints
    GROQ_API_BASE: str = "https://api.groq.com/openai/v1"
    SERPER_API_BASE: str = "https://google.serper.dev/search"
    
    # Satellite Data APIs (Free/Open APIs)
    SATELLITE_APIS: Dict[str, str] = {
        "nasa_earth": "https://api.nasa.gov/planetary/earth/imagery",
        "sentinel_hub": "https://services.sentinel-hub.com/api/v1",
        "open_weather": "https://api.openweathermap.org/data/2.5",
    }
    
    # Timeout Settings
    SATELLITE_API_TIMEOUT: int = int(os.getenv("SATELLITE_API_TIMEOUT", "30"))
    REGULATORY_API_TIMEOUT: int = int(os.getenv("REGULATORY_API_TIMEOUT", "15"))
    LLM_REQUEST_TIMEOUT: int = int(os.getenv("LLM_REQUEST_TIMEOUT", "30"))
    
    # Cache Settings
    REGULATORY_CACHE_HOURS: int = int(os.getenv("REGULATORY_CACHE_HOURS", "24"))
    SATELLITE_CACHE_HOURS: int = int(os.getenv("SATELLITE_CACHE_HOURS", "6"))
    
    # Validation Thresholds
    MIN_COORDINATE_ACCURACY: float = float(os.getenv("MIN_COORDINATE_ACCURACY", "0.001"))
    MAX_HARVEST_AGE_DAYS: int = int(os.getenv("MAX_HARVEST_AGE_DAYS", "7"))
    COMPLIANCE_CONFIDENCE_THRESHOLD: float = float(os.getenv("COMPLIANCE_CONFIDENCE_THRESHOLD", "0.7"))
    
    # Ayurvedic Species Database
    AYURVEDIC_SPECIES: Dict[str, Dict[str, Any]] = {
        "ashwagandha": {
            "scientific_name": "Withania somnifera",
            "harvest_season": ["winter", "post_monsoon"],
            "restricted_regions": [],
            "conservation_status": "least_concern"
        },
        "brahmi": {
            "scientific_name": "Bacopa monnieri",
            "harvest_season": ["monsoon", "post_monsoon"],
            "restricted_regions": ["wetlands"],
            "conservation_status": "vulnerable"
        },
        "turmeric": {
            "scientific_name": "Curcuma longa",
            "harvest_season": ["post_monsoon", "winter"],
            "restricted_regions": [],
            "conservation_status": "least_concern"
        },
        "neem": {
            "scientific_name": "Azadirachta indica",
            "harvest_season": ["summer", "winter"],
            "restricted_regions": [],
            "conservation_status": "least_concern"
        },
        "tulsi": {
            "scientific_name": "Ocimum tenuiflorum",
            "harvest_season": ["summer", "post_monsoon"],
            "restricted_regions": [],
            "conservation_status": "least_concern"
        }
    }
    
    # Indian States and Regions
    INDIAN_REGIONS: Dict[str, List[str]] = {
        "northern": ["punjab", "haryana", "himachal pradesh", "uttarakhand", "uttar pradesh", "delhi"],
        "southern": ["tamil nadu", "kerala", "karnataka", "andhra pradesh", "telangana"],
        "western": ["maharashtra", "gujarat", "rajasthan", "goa", "mp"],
        "eastern": ["west bengal", "odisha", "bihar", "jharkhand", "assam"],
        "central": ["madhya pradesh", "chhattisgarh"],
        "northeastern": ["assam", "meghalaya", "tripura", "mizoram", "manipur", "nagaland", "arunachal pradesh", "sikkim"]
    }
    
    # Regulatory Bodies
    REGULATORY_AUTHORITIES: List[str] = [
        "NMPB", "AYUSH", "FSSAI", "APEDA", "Central Drug Standard Control Organization",
        "National Medicinal Plants Board", "Ministry of AYUSH"
    ]
    
    # Compliance Standards
    QUALITY_STANDARDS: Dict[str, Dict[str, Any]] = {
        "moisture_content": {"max": 12.0, "unit": "percentage"},
        "ash_content": {"max": 10.0, "unit": "percentage"},
        "heavy_metals": {
            "lead": {"max": 10.0, "unit": "ppm"},
            "mercury": {"max": 1.0, "unit": "ppm"},
            "cadmium": {"max": 0.3, "unit": "ppm"}
        },
        "pesticide_residues": {"max": 0.01, "unit": "ppm"}
    }
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate that required configuration is present."""
        required_keys = ["GROQ_API_KEY", "SERPER_API_KEY"]
        missing_keys = [key for key in required_keys if not getattr(cls, key)]
        
        if missing_keys:
            raise ValueError(f"Missing required configuration: {missing_keys}")
        
        return True

# Global settings instance
settings = Settings()