"""
Utility functions and helpers for VrukshaChain.
"""
import json
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from geopy.distance import geodesic
from config.settings import settings
from utils.logger import get_logger

logger = get_logger("helpers")

def generate_event_id() -> str:
    """Generate a unique event ID."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_suffix = str(uuid.uuid4())[:8]
    return f"VRC_{timestamp}_{unique_suffix}"

def calculate_distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
    """Calculate distance between two coordinates in kilometers."""
    try:
        return geodesic(coord1, coord2).kilometers
    except Exception as e:
        logger.error(f"Error calculating distance: {str(e)}")
        return 0.0

def format_coordinates(lat: float, lon: float) -> str:
    """Format coordinates for display."""
    lat_dir = "N" if lat >= 0 else "S"
    lon_dir = "E" if lon >= 0 else "W"
    return f"{abs(lat):.6f}°{lat_dir}, {abs(lon):.6f}°{lon_dir}"

def validate_coordinates(lat: float, lon: float) -> bool:
    """Validate coordinate values."""
    return -90 <= lat <= 90 and -180 <= lon <= 180

def calculate_harvest_season(date: datetime) -> str:
    """Determine harvest season based on date."""
    month = date.month
    
    if month in [12, 1, 2]:
        return "winter"
    elif month in [3, 4, 5]:
        return "spring"
    elif month in [6, 7, 8]:
        return "monsoon"
    elif month in [9, 10, 11]:
        return "post_monsoon"
    else:
        return "unknown"

def is_harvest_season_valid(species: str, harvest_date: datetime) -> bool:
    """Check if harvest date is valid for the species."""
    species_info = settings.AYURVEDIC_SPECIES.get(species.lower())
    if not species_info:
        logger.warning(f"Species {species} not found in database")
        return True  # Allow unknown species
    
    current_season = calculate_harvest_season(harvest_date)
    allowed_seasons = species_info.get("harvest_season", [])
    
    return current_season in allowed_seasons

def calculate_age_from_harvest(harvest_date: datetime) -> int:
    """Calculate days since harvest."""
    return (datetime.now() - harvest_date).days

def is_harvest_recent(harvest_date: datetime) -> bool:
    """Check if harvest is within acceptable age limit."""
    age_days = calculate_age_from_harvest(harvest_date)
    return age_days <= settings.MAX_HARVEST_AGE_DAYS

def hash_data(data: Any) -> str:
    """Create SHA256 hash of data for integrity verification."""
    json_str = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(json_str.encode()).hexdigest()

def sanitize_input(text: str) -> str:
    """Sanitize user input text."""
    if not text:
        return ""
    
    # Remove potentially harmful characters
    sanitized = "".join(char for char in text if char.isprintable())
    return sanitized.strip()

def format_percentage(value: float, decimals: int = 1) -> str:
    """Format a decimal value as a percentage."""
    return f"{value * 100:.{decimals}f}%"

def format_currency(amount: float, currency: str = "INR") -> str:
    """Format currency amount."""
    return f"{currency} {amount:,.2f}"

def get_indian_state_from_coordinates(lat: float, lon: float) -> Optional[str]:
    """Approximate Indian state from coordinates (simplified)."""
    # This is a simplified mapping - in production, use proper geocoding service
    state_mappings = {
        (20, 30, 68, 78): "rajasthan",
        (15, 25, 72, 80): "maharashtra", 
        (8, 18, 76, 80): "tamil_nadu",
        (8, 18, 74, 78): "kerala",
        (11, 18, 74, 80): "karnataka",
        (25, 35, 75, 85): "uttar_pradesh",
        (28, 32, 76, 78): "haryana",
        (30, 33, 76, 78): "himachal_pradesh"
    }
    
    for (min_lat, max_lat, min_lon, max_lon), state in state_mappings.items():
        if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
            return state
    
    return None

def determine_region_from_state(state: str) -> Optional[str]:
    """Determine Indian region from state."""
    for region, states in settings.INDIAN_REGIONS.items():
        if state.lower() in states:
            return region
    return None

def create_compliance_summary(violations: List[str], warnings: List[str]) -> str:
    """Create a human-readable compliance summary."""
    if not violations and not warnings:
        return "✅ Full compliance - All requirements met"
    elif violations:
        return f"❌ Non-compliant - {len(violations)} violation(s) found"
    elif warnings:
        return f"⚠️ Compliant with warnings - {len(warnings)} warning(s)"
    else:
        return "📋 Compliance status unknown"

def extract_species_from_text(text: str) -> Optional[str]:
    """Extract species name from text input."""
    text_lower = text.lower()
    
    # Check against known species
    for species in settings.AYURVEDIC_SPECIES.keys():
        if species in text_lower:
            return species
    
    # Check against scientific names
    for species, info in settings.AYURVEDIC_SPECIES.items():
        scientific_name = info.get("scientific_name", "").lower()
        if scientific_name in text_lower:
            return species
    
    return None

def format_validation_report(result: Dict[str, Any]) -> str:
    """Format validation result as a readable report."""
    lines = [
        "=" * 50,
        "VRUKSHACHAIN VALIDATION REPORT",
        "=" * 50,
        f"Event ID: {result.get('event_id', 'N/A')}",
        f"Validation Time: {result.get('validation_timestamp', 'N/A')}",
        f"Overall Status: {result.get('overall_status', 'N/A')}",
        f"Confidence Score: {format_percentage(result.get('confidence_score', 0))}",
        "",
        "SUMMARY:",
        result.get('compliance_summary', 'No summary available'),
        ""
    ]
    
    if result.get('warnings'):
        lines.extend([
            "WARNINGS:",
            *[f"• {warning}" for warning in result['warnings']],
            ""
        ])
    
    if result.get('recommendations'):
        lines.extend([
            "RECOMMENDATIONS:",
            *[f"• {rec}" for rec in result['recommendations']],
            ""
        ])
    
    if result.get('next_steps'):
        lines.extend([
            "NEXT STEPS:",
            *[f"• {step}" for step in result['next_steps']],
            ""
        ])
    
    lines.append("=" * 50)
    return "\n".join(lines)

def chunk_text(text: str, max_length: int = 2000) -> List[str]:
    """Split text into chunks for API calls."""
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    words = text.split()
    current_chunk = []
    current_length = 0
    
    for word in words:
        word_length = len(word) + 1  # +1 for space
        if current_length + word_length > max_length:
            if current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_length = len(word)
            else:
                # Single word is too long, split it
                chunks.append(word[:max_length])
                current_chunk = [word[max_length:]] if len(word) > max_length else []
                current_length = len(current_chunk[0]) if current_chunk else 0
        else:
            current_chunk.append(word)
            current_length += word_length
    
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    return chunks

def merge_validation_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge multiple validation results into one comprehensive result."""
    if not results:
        return {}
    
    if len(results) == 1:
        return results[0]
    
    merged = {
        "event_id": results[0].get("event_id"),
        "validation_timestamp": datetime.now(),
        "overall_status": "pending",
        "confidence_score": 0.0,
        "compliance_summary": "",
        "recommendations": [],
        "warnings": [],
        "next_steps": [],
        "data_sources_used": []
    }
    
    # Merge all recommendations, warnings, etc.
    all_recommendations = []
    all_warnings = []
    all_next_steps = []
    all_sources = []
    confidence_scores = []
    
    for result in results:
        all_recommendations.extend(result.get("recommendations", []))
        all_warnings.extend(result.get("warnings", []))
        all_next_steps.extend(result.get("next_steps", []))
        all_sources.extend(result.get("data_sources_used", []))
        
        if result.get("confidence_score"):
            confidence_scores.append(result["confidence_score"])
    
    # Remove duplicates
    merged["recommendations"] = list(set(all_recommendations))
    merged["warnings"] = list(set(all_warnings))
    merged["next_steps"] = list(set(all_next_steps))
    merged["data_sources_used"] = list(set(all_sources))
    
    # Calculate average confidence
    if confidence_scores:
        merged["confidence_score"] = sum(confidence_scores) / len(confidence_scores)
    
    # Determine overall status
    statuses = [r.get("overall_status") for r in results if r.get("overall_status")]
    if "non_compliant" in statuses:
        merged["overall_status"] = "non_compliant"
    elif "requires_review" in statuses:
        merged["overall_status"] = "requires_review"
    elif "compliant" in statuses:
        merged["overall_status"] = "compliant"
    
    # Create summary
    merged["compliance_summary"] = create_compliance_summary(
        [w for w in merged["warnings"] if "violation" in w.lower()],
        [w for w in merged["warnings"] if "violation" not in w.lower()]
    )
    
    return merged

def format_time_duration(seconds: float) -> str:
    """Format duration in seconds to human readable format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to specified length with suffix."""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def normalize_species_name(name: str) -> str:
    """Normalize species name for consistent lookup."""
    return name.lower().strip().replace(" ", "_").replace("-", "_")

def get_quality_status(value: float, standard: Dict[str, Any]) -> str:
    """Get quality status based on value and standard."""
    if "max" in standard:
        return "compliant" if value <= standard["max"] else "non_compliant"
    elif "min" in standard:
        return "compliant" if value >= standard["min"] else "non_compliant"
    elif "range" in standard:
        min_val, max_val = standard["range"]
        return "compliant" if min_val <= value <= max_val else "non_compliant"
    else:
        return "unknown"

def calculate_compliance_score(results: List[Dict[str, Any]]) -> float:
    """Calculate overall compliance score from individual results."""
    if not results:
        return 0.0
    
    compliant_count = 0
    total_count = len(results)
    
    for result in results:
        status = result.get("status", "unknown")
        if status == "compliant":
            compliant_count += 1
        elif status == "requires_review":
            compliant_count += 0.5  # Partial credit
    
    return compliant_count / total_count

def format_scientific_name(scientific_name: str) -> str:
    """Format scientific name with proper italics markup."""
    return f"*{scientific_name}*"

def get_conservation_color(status: str) -> str:
    """Get color code for conservation status."""
    color_map = {
        "extinct": "#000000",
        "critically_endangered": "#FF0000",
        "endangered": "#FF6600",
        "vulnerable": "#FFCC00",
        "near_threatened": "#CCFF00",
        "least_concern": "#00FF00",
        "data_deficient": "#999999"
    }
    return color_map.get(status.lower(), "#999999")

def validate_quality_metrics(metrics: Dict[str, float]) -> List[str]:
    """Validate quality metrics against standards and return issues."""
    issues = []
    
    for param, value in metrics.items():
        if param in settings.QUALITY_STANDARDS:
            standard = settings.QUALITY_STANDARDS[param]
            status = get_quality_status(value, standard)
            
            if status == "non_compliant":
                if "max" in standard:
                    issues.append(f"{param}: {value} exceeds maximum of {standard['max']}")
                elif "min" in standard:
                    issues.append(f"{param}: {value} below minimum of {standard['min']}")
                elif "range" in standard:
                    min_val, max_val = standard["range"]
                    issues.append(f"{param}: {value} outside range {min_val}-{max_val}")
    
    return issues

def generate_qr_data(event_id: str, validation_result: Dict[str, Any]) -> str:
    """Generate QR code data string for collection event."""
    qr_data = {
        "event_id": event_id,
        "validation_status": validation_result.get("overall_status"),
        "confidence_score": validation_result.get("confidence_score"),
        "validation_timestamp": str(validation_result.get("validation_timestamp", datetime.now())),
        "vrukshachain_version": settings.APP_VERSION
    }
    
    return json.dumps(qr_data, separators=(',', ':'))

def parse_location_string(location_str: str) -> Optional[Tuple[float, float]]:
    """Parse location string into latitude, longitude tuple."""
    try:
        # Handle various formats: "lat,lon", "lat, lon", "(lat, lon)", etc.
        location_str = location_str.strip("() ")
        parts = [part.strip() for part in location_str.split(",")]
        
        if len(parts) == 2:
            lat = float(parts[0])
            lon = float(parts[1])
            
            if validate_coordinates(lat, lon):
                return (lat, lon)
    
    except (ValueError, IndexError):
        pass
    
    return None

def get_season_emoji(season: str) -> str:
    """Get emoji for harvest season."""
    season_emojis = {
        "spring": "🌸",
        "summer": "☀️", 
        "monsoon": "🌧️",
        "post_monsoon": "🌾",
        "winter": "❄️"
    }
    return season_emojis.get(season.lower(), "🌿")

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024**2:
        return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024**3:
        return f"{size_bytes/1024**2:.1f} MB"
    else:
        return f"{size_bytes/1024**3:.1f} GB"