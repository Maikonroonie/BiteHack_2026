"""
CrisisEye - OpenStreetMap Service
Pobieranie budynków i infrastruktury z OSM Overpass API.
"""

import httpx
from typing import List, Dict, Any
import asyncio

from models.schemas import BuildingInfo


class OSMService:
    """
    Serwis do pobierania danych z OpenStreetMap.
    Używa Overpass API do zapytań o budynki.
    """
    
    def __init__(self):
        self.overpass_url = "https://overpass-api.de/api/interpreter"
        self.timeout = 30.0
    
    async def get_buildings(self, bbox: List[float]) -> List[BuildingInfo]:
        """
        Pobiera budynki z OSM dla zadanego obszaru.
        
        Args:
            bbox: Bounding box [minLon, minLat, maxLon, maxLat]
            
        Returns:
            Lista budynków jako BuildingInfo
        """
        # Format dla Overpass: (south,west,north,east)
        overpass_bbox = f"{bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]}"
        
        query = f"""
        [out:json][timeout:25];
        (
          way["building"]({overpass_bbox});
          relation["building"]({overpass_bbox});
        );
        out center;
        """
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.overpass_url,
                    data={"data": query},
                    timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json()
                
                return self._parse_buildings(data)
                
        except httpx.TimeoutException:
            print("⚠️ OSM request timed out, returning demo data")
            return self._get_demo_buildings(bbox)
        except Exception as e:
            print(f"⚠️ OSM error: {e}, returning demo data")
            return self._get_demo_buildings(bbox)
    
    def _parse_buildings(self, data: Dict[str, Any]) -> List[BuildingInfo]:
        """Parsuje odpowiedź Overpass do listy BuildingInfo."""
        buildings = []
        
        elements = data.get("elements", [])
        
        for element in elements:
            # Pobierz centrum budynku
            if "center" in element:
                lat = element["center"]["lat"]
                lon = element["center"]["lon"]
            else:
                continue
            
            tags = element.get("tags", {})
            
            buildings.append(BuildingInfo(
                osm_id=element.get("id", 0),
                name=tags.get("name"),
                building_type=tags.get("building", "yes"),
                lat=lat,
                lon=lon,
                is_flooded=False,
                flood_probability=0.0
            ))
        
        return buildings
    
    def _get_demo_buildings(self, bbox: List[float]) -> List[BuildingInfo]:
        """
        Generuje demo budynki gdy OSM jest niedostępne.
        """
        import random
        random.seed(42)
        
        buildings = []
        n_buildings = 50
        
        for i in range(n_buildings):
            lat = random.uniform(bbox[1], bbox[3])
            lon = random.uniform(bbox[0], bbox[2])
            
            building_types = ["residential", "commercial", "industrial", "school", "hospital"]
            
            buildings.append(BuildingInfo(
                osm_id=1000000 + i,
                name=f"Building {i+1}" if random.random() > 0.7 else None,
                building_type=random.choice(building_types),
                lat=lat,
                lon=lon,
                is_flooded=False,
                flood_probability=0.0
            ))
        
        return buildings
    
    async def get_infrastructure(
        self, 
        bbox: List[float],
        infra_type: str = "highway"
    ) -> List[Dict[str, Any]]:
        """
        Pobiera infrastrukturę (drogi, mosty, etc.) z OSM.
        
        Args:
            bbox: Bounding box
            infra_type: Typ infrastruktury (highway, bridge, railway)
            
        Returns:
            Lista elementów infrastruktury
        """
        overpass_bbox = f"{bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]}"
        
        query = f"""
        [out:json][timeout:25];
        way["{infra_type}"]({overpass_bbox});
        out geom;
        """
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.overpass_url,
                    data={"data": query},
                    timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json()
                
                return data.get("elements", [])
                
        except Exception as e:
            print(f"⚠️ Infrastructure query failed: {e}")
            return []
