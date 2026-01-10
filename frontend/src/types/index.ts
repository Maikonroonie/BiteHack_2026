/**
 * CrisisEye - TypeScript Types
 * Definicje typów dla API i komponentów
 */

// Bounding Box
export interface BoundingBox {
  min_lon: number;
  min_lat: number;
  max_lon: number;
  max_lat: number;
}

// Analysis Request
export interface AnalysisRequest {
  bbox: BoundingBox;
  date_before: string;
  date_after: string;
  polarization?: "VV" | "VH";
}

// Flood Statistics
export interface FloodPixelStats {
  total_pixels: number;
  flooded_pixels: number;
  flood_percentage: number;
  area_km2: number;
  flooded_area_km2: number;
}

// Building Info
export interface BuildingInfo {
  osm_id: number;
  name: string | null;
  building_type: string;
  lat: number;
  lon: number;
  is_flooded: boolean;
  flood_probability: number;
}

// GeoJSON Feature
export interface FloodFeature {
  type: "Feature";
  properties: {
    flood_probability: number;
    area_km2?: number;
    cell_size_deg?: number;
  };
  geometry: {
    type: "Polygon";
    coordinates: number[][][];
  };
}

// GeoJSON FeatureCollection
export interface FloodGeoJSON {
  type: "FeatureCollection";
  features: FloodFeature[];
}

// Analysis Response
export interface AnalysisResponse {
  status: "pending" | "processing" | "completed" | "failed";
  message: string;
  stats: FloodPixelStats | null;
  flood_geojson: FloodGeoJSON | null;
  buildings_affected: number;
  processing_time_seconds: number;
}

// Buildings Response
export interface BuildingsResponse {
  total_count: number;
  flooded_count: number;
  buildings: BuildingInfo[];
}

// Health Response
export interface HealthResponse {
  status: string;
  version: string;
  services: Record<string, string>;
}

// Map State
export interface MapState {
  center: [number, number];
  zoom: number;
  bounds: BoundingBox | null;
}

// Analysis Form State
export interface AnalysisFormState {
  bbox: BoundingBox;
  dateBefore: string;
  dateAfter: string;
  polarization: "VV" | "VH";
  isLoading: boolean;
  error: string | null;
}

// App State
export interface AppState {
  analysisResult: AnalysisResponse | null;
  buildings: BuildingInfo[];
  isAnalyzing: boolean;
  selectedArea: BoundingBox | null;
}

//PREDICTION / NOWCASTING TYPES

// Prediction Request
export interface PredictionRequest {
  bbox: BoundingBox;
  prediction_hours: number;
}

// Evacuation Priority
export interface EvacuationPriority {
  osm_id: number;
  name: string | null;
  building_type: string;
  lat: number;
  lon: number;
  risk_level: "critical" | "high" | "medium" | "low";
  flood_probability: number;
  evacuation_score: number;
  estimated_time_to_flood_hours: number;
  people_estimate: number;
}

// Precipitation Info
export interface PrecipitationInfo {
  mean_mm: number;
  max_mm: number;
  source: string;
  hours_analyzed: number;
  is_simulated: boolean;
}

// Risk Factors
export interface RiskFactors {
  precipitation_contribution: number;
  terrain_contribution: number;
  time_factor: number;
}

// Prediction Response
export interface PredictionResponse {
  status: "pending" | "processing" | "completed" | "failed";
  message: string;
  timestamp: string;
  prediction_hours: number;
  flood_probability: number;
  risk_level: "low" | "moderate" | "high" | "critical" | "unknown";
  confidence: number;
  precipitation: PrecipitationInfo | null;
  risk_factors: RiskFactors | null;
  risk_zones_geojson: FloodGeoJSON | null;
  evacuation_priorities: EvacuationPriority[];
  processing_time_seconds: number;
  next_update_minutes: number;
}
