"""
Serper API agent for web search capabilities.
"""
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional
from datetime import datetime

from config.settings import settings
from models.schemas import AgentResponse
from utils.logger import get_logger
from utils.helpers import sanitize_input, chunk_text

logger = get_logger("serper_agent")

class SerperAgent:
    """Agent for handling web search via Serper API."""
    
    def __init__(self):
        self.api_key = settings.SERPER_API_KEY
        self.base_url = settings.SERPER_API_BASE
        self.timeout = settings.REGULATORY_API_TIMEOUT
        
    async def search_regulatory_info(self, species: str, region: str = "india") -> AgentResponse:
        """Search for regulatory information about a specific species."""
        try:
            query = f"AYUSH NMPB {species} harvesting regulations guidelines {region}"
            query = sanitize_input(query)
            
            logger.info(f"Searching regulatory info for: {query}")
            
            result = await self._perform_search(query)
            
            if result.get("organic"):
                regulatory_data = self._extract_regulatory_info(result["organic"], species)
                return AgentResponse(
                    success=True,
                    data=regulatory_data,
                    message=f"Found {len(regulatory_data.get('requirements', []))} regulatory requirements",
                    source="serper_web_search"
                )
            else:
                return AgentResponse(
                    success=False,
                    message="No regulatory information found",
                    error="No search results returned",
                    source="serper_web_search"
                )
                
        except Exception as e:
            logger.error(f"Error searching regulatory info: {str(e)}")
            return AgentResponse(
                success=False,
                message="Failed to search regulatory information",
                error=str(e),
                source="serper_web_search"
            )
    
    async def search_species_info(self, species: str) -> AgentResponse:
        """Search for general information about an Ayurvedic species."""
        try:
            query = f"{species} ayurvedic herb scientific name properties harvesting"
            query = sanitize_input(query)
            
            logger.info(f"Searching species info for: {query}")
            
            result = await self._perform_search(query)
            
            if result.get("organic"):
                species_data = self._extract_species_info(result["organic"], species)
                return AgentResponse(
                    success=True,
                    data=species_data,
                    message=f"Found information about {species}",
                    source="serper_web_search"
                )
            else:
                return AgentResponse(
                    success=False,
                    message="No species information found",
                    error="No search results returned",
                    source="serper_web_search"
                )
                
        except Exception as e:
            logger.error(f"Error searching species info: {str(e)}")
            return AgentResponse(
                success=False,
                message="Failed to search species information",
                error=str(e),
                source="serper_web_search"
            )
    
    async def search_conservation_status(self, species: str, scientific_name: str = "") -> AgentResponse:
        """Search for conservation status of a species."""
        try:
            search_terms = [species]
            if scientific_name:
                search_terms.append(scientific_name)
            
            query = f"conservation status endangered {' '.join(search_terms)} IUCN red list"
            query = sanitize_input(query)
            
            logger.info(f"Searching conservation status for: {query}")
            
            result = await self._perform_search(query)
            
            if result.get("organic"):
                conservation_data = self._extract_conservation_info(result["organic"], species)
                return AgentResponse(
                    success=True,
                    data=conservation_data,
                    message=f"Found conservation status for {species}",
                    source="serper_web_search"
                )
            else:
                return AgentResponse(
                    success=False,
                    message="No conservation information found",
                    error="No search results returned",
                    source="serper_web_search"
                )
                
        except Exception as e:
            logger.error(f"Error searching conservation status: {str(e)}")
            return AgentResponse(
                success=False,
                message="Failed to search conservation status",
                error=str(e),
                source="serper_web_search"
            )
    
    async def search_seasonal_restrictions(self, species: str, region: str = "") -> AgentResponse:
        """Search for seasonal harvesting restrictions."""
        try:
            location_term = f"{region} India" if region else "India"
            query = f"{species} harvesting season restrictions {location_term} NMPB guidelines"
            query = sanitize_input(query)
            
            logger.info(f"Searching seasonal restrictions for: {query}")
            
            result = await self._perform_search(query)
            
            if result.get("organic"):
                seasonal_data = self._extract_seasonal_info(result["organic"], species)
                return AgentResponse(
                    success=True,
                    data=seasonal_data,
                    message=f"Found seasonal information for {species}",
                    source="serper_web_search"
                )
            else:
                return AgentResponse(
                    success=False,
                    message="No seasonal restriction information found",
                    error="No search results returned",
                    source="serper_web_search"
                )
                
        except Exception as e:
            logger.error(f"Error searching seasonal restrictions: {str(e)}")
            return AgentResponse(
                success=False,
                message="Failed to search seasonal restrictions",
                error=str(e),
                source="serper_web_search"
            )
    
    async def _perform_search(self, query: str) -> Dict[str, Any]:
        """Perform the actual search request."""
        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "q": query,
            "num": 10,  # Number of results
            "gl": "in",  # India
            "hl": "en"   # English
        }
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
            async with session.post(self.base_url, json=payload, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"Serper API error {response.status}: {error_text}")
                    raise Exception(f"API request failed with status {response.status}")
    
    def _extract_regulatory_info(self, search_results: List[Dict], species: str) -> Dict[str, Any]:
        """Extract regulatory information from search results."""
        regulatory_data = {
            "species": species,
            "authorities": [],
            "requirements": [],
            "restrictions": [],
            "sources": []
        }
        
        regulatory_keywords = [
            "NMPB", "AYUSH", "regulation", "guideline", "standard",
            "harvesting", "collection", "restriction", "banned", "protected"
        ]
        
        for result in search_results[:5]:  # Check top 5 results
            title = result.get("title", "").lower()
            snippet = result.get("snippet", "").lower()
            url = result.get("link", "")
            
            # Check if result is relevant to regulations
            if any(keyword in title or keyword in snippet for keyword in regulatory_keywords):
                regulatory_data["sources"].append({
                    "title": result.get("title", ""),
                    "url": url,
                    "snippet": result.get("snippet", "")
                })
                
                # Extract specific requirements
                content = f"{title} {snippet}"
                if "harvest" in content and ("season" in content or "time" in content):
                    regulatory_data["requirements"].append("Seasonal harvesting restrictions apply")
                
                if "license" in content or "permit" in content:
                    regulatory_data["requirements"].append("Collection license/permit required")
                
                if "protected" in content or "endangered" in content:
                    regulatory_data["restrictions"].append("Species may be protected or endangered")
                
                if "NMPB" in content:
                    regulatory_data["authorities"].append("National Medicinal Plants Board (NMPB)")
                
                if "AYUSH" in content:
                    regulatory_data["authorities"].append("Ministry of AYUSH")
        
        # Remove duplicates
        regulatory_data["authorities"] = list(set(regulatory_data["authorities"]))
        regulatory_data["requirements"] = list(set(regulatory_data["requirements"]))
        regulatory_data["restrictions"] = list(set(regulatory_data["restrictions"]))
        
        return regulatory_data
    
    def _extract_species_info(self, search_results: List[Dict], species: str) -> Dict[str, Any]:
        """Extract species information from search results."""
        species_data = {
            "common_name": species,
            "scientific_name": "",
            "properties": [],
            "uses": [],
            "habitat": "",
            "sources": []
        }
        
        for result in search_results[:3]:  # Check top 3 results
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            url = result.get("link", "")
            
            species_data["sources"].append({
                "title": title,
                "url": url,
                "snippet": snippet
            })
            
            # Try to extract scientific name
            content = snippet.lower()
            if "scientific name" in content:
                # Simple extraction - in production, use more sophisticated NLP
                words = snippet.split()
                for i, word in enumerate(words):
                    if "scientific" in word.lower() and i < len(words) - 2:
                        potential_name = f"{words[i+2]} {words[i+3] if i+3 < len(words) else ''}"
                        if potential_name.count(' ') == 1:  # Likely binomial name
                            species_data["scientific_name"] = potential_name.strip()
                        break
        
        return species_data
    
    def _extract_conservation_info(self, search_results: List[Dict], species: str) -> Dict[str, Any]:
        """Extract conservation information from search results."""
        conservation_data = {
            "species": species,
            "conservation_status": "unknown",
            "threats": [],
            "protection_measures": [],
            "sources": []
        }
        
        status_keywords = {
            "extinct": "extinct",
            "critically endangered": "critically_endangered",
            "endangered": "endangered", 
            "vulnerable": "vulnerable",
            "near threatened": "near_threatened",
            "least concern": "least_concern"
        }
        
        for result in search_results[:3]:
            title = result.get("title", "").lower()
            snippet = result.get("snippet", "").lower()
            url = result.get("link", "")
            
            conservation_data["sources"].append({
                "title": result.get("title", ""),
                "url": url,
                "snippet": result.get("snippet", "")
            })
            
            content = f"{title} {snippet}"
            
            # Check for conservation status
            for keyword, status in status_keywords.items():
                if keyword in content:
                    conservation_data["conservation_status"] = status
                    break
            
            # Extract threats
            if "threat" in content or "declining" in content:
                conservation_data["threats"].append("Population declining due to various threats")
            
            if "habitat loss" in content:
                conservation_data["threats"].append("Habitat loss")
            
            if "overharvesting" in content or "over-collection" in content:
                conservation_data["threats"].append("Overharvesting/over-collection")
        
        # Remove duplicates
        conservation_data["threats"] = list(set(conservation_data["threats"]))
        conservation_data["protection_measures"] = list(set(conservation_data["protection_measures"]))
        
        return conservation_data
    
    def _extract_seasonal_info(self, search_results: List[Dict], species: str) -> Dict[str, Any]:
        """Extract seasonal harvesting information from search results."""
        seasonal_data = {
            "species": species,
            "harvest_seasons": [],
            "restrictions": [],
            "best_practices": [],
            "sources": []
        }
        
        season_keywords = ["summer", "winter", "monsoon", "spring", "rainy season", "dry season"]
        
        for result in search_results[:3]:
            title = result.get("title", "").lower()
            snippet = result.get("snippet", "").lower()
            url = result.get("link", "")
            
            seasonal_data["sources"].append({
                "title": result.get("title", ""),
                "url": url,
                "snippet": result.get("snippet", "")
            })
            
            content = f"{title} {snippet}"
            
            # Extract harvest seasons
            for season in season_keywords:
                if season in content and ("harvest" in content or "collect" in content):
                    seasonal_data["harvest_seasons"].append(season)
            
            # Extract restrictions
            if "avoid" in content and any(season in content for season in season_keywords):
                seasonal_data["restrictions"].append("Certain seasons should be avoided for harvesting")
            
            if "flowering" in content:
                seasonal_data["best_practices"].append("Consider plant flowering cycle when harvesting")
        
        # Remove duplicates
        seasonal_data["harvest_seasons"] = list(set(seasonal_data["harvest_seasons"]))
        seasonal_data["restrictions"] = list(set(seasonal_data["restrictions"]))
        seasonal_data["best_practices"] = list(set(seasonal_data["best_practices"]))
        
        return seasonal_data