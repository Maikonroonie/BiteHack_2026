/**
 * CrisisEye - API Service
 * Komunikacja z backendem FastAPI
 */

import axios from "axios";
import type {
  AnalysisRequest,
  AnalysisResponse,
  BuildingsResponse,
  BoundingBox,
  HealthResponse,
  PredictionRequest,
  PredictionResponse,
} from "../types";

// Base URL - z Vite proxy lub env
const API_BASE_URL = import.meta.env.VITE_API_URL || "";

// Axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60s dla długich analiz
  headers: {
    "Content-Type": "application/json",
  },
});

/**
 * Health check
 */
export async function checkHealth(): Promise<HealthResponse> {
  const response = await api.get<HealthResponse>("/health");
  return response.data;
}

/**
 * Główna analiza powodzi
 */
export async function analyzeFlood(
  request: AnalysisRequest
): Promise<AnalysisResponse> {
  const response = await api.post<AnalysisResponse>("/api/analyze", request);
  return response.data;
}

/**
 * Pobierz maskę powodzi
 */
export async function getFloodMask(
  request: AnalysisRequest
): Promise<AnalysisResponse> {
  const response = await api.post<AnalysisResponse>("/api/flood-mask", request);
  return response.data;
}

/**
 * Pobierz budynki z OSM
 */
export async function getBuildings(
  bbox: BoundingBox
): Promise<BuildingsResponse> {
  const response = await api.post<BuildingsResponse>("/api/buildings", {
    bbox,
  });
  return response.data;
}

/**
 * Pobierz demo dane (bez prawdziwego przetwarzania SAR)
 */
export async function getDemoData(): Promise<AnalysisResponse> {
  const response = await api.get<AnalysisResponse>("/api/demo");
  return response.data;
}

//PREDICTION / NOWCASTING API

/**
 * Predykcja powodzi w czasie rzeczywistym (AI)
 */
export async function predictFlood(
  request: PredictionRequest
): Promise<PredictionResponse> {
  const response = await api.post<PredictionResponse>("/api/predict", request);
  return response.data;
}

/**
 * Demo predykcji dla Wrocławia
 */
export async function getPredictionDemo(): Promise<PredictionResponse> {
  const response = await api.get<PredictionResponse>("/api/predict/demo");
  return response.data;
}

/**
 * Helper do formatowania dat dla API
 */
export function formatDateForApi(date: Date): string {
  return date.toISOString().split("T")[0];
}

/**
 * Helper do tworzenia bbox z bounds mapy
 */
export function createBboxFromBounds(
  southWest: { lat: number; lng: number },
  northEast: { lat: number; lng: number }
): BoundingBox {
  return {
    min_lon: southWest.lng,
    min_lat: southWest.lat,
    max_lon: northEast.lng,
    max_lat: northEast.lat,
  };
}

export default api;
