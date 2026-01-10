/**
 * CrisisEye - useFloodData Hook
 * Custom hook do zarządzania stanem analizy powodzi
 */

import { useState, useCallback } from 'react';
import type {
    AnalysisResponse,
    AnalysisRequest,
    BuildingInfo,
    BoundingBox
} from '../types';
import { analyzeFlood, getBuildings, getDemoData } from '../services/api';

interface FloodDataState {
    result: AnalysisResponse | null;
    buildings: BuildingInfo[];
    isLoading: boolean;
    error: string | null;
}

export function useFloodData() {
    const [state, setState] = useState<FloodDataState>({
        result: null,
        buildings: [],
        isLoading: false,
        error: null,
    });

    /**
     * Uruchom pełną analizę powodzi
     */
    const runAnalysis = useCallback(async (request: AnalysisRequest) => {
        setState(prev => ({ ...prev, isLoading: true, error: null }));

        try {
            const result = await analyzeFlood(request);

            // Pobierz budynki dla obszaru
            const buildingsData = await getBuildings(request.bbox);

            setState({
                result,
                buildings: buildingsData.buildings,
                isLoading: false,
                error: null,
            });

            return result;
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Nieznany błąd';
            setState(prev => ({
                ...prev,
                isLoading: false,
                error: errorMessage,
            }));
            throw err;
        }
    }, []);

    /**
     * Załaduj demo dane (bez prawdziwej analizy)
     */
    const loadDemoData = useCallback(async () => {
        setState(prev => ({ ...prev, isLoading: true, error: null }));

        try {
            const result = await getDemoData();

            setState({
                result,
                buildings: [], // Demo nie ma prawdziwych budynków
                isLoading: false,
                error: null,
            });

            return result;
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Nieznany błąd';
            setState(prev => ({
                ...prev,
                isLoading: false,
                error: errorMessage,
            }));
            throw err;
        }
    }, []);

    /**
     * Pobierz budynki dla obszaru
     */
    const fetchBuildings = useCallback(async (bbox: BoundingBox) => {
        try {
            const buildingsData = await getBuildings(bbox);
            setState(prev => ({
                ...prev,
                buildings: buildingsData.buildings,
            }));
            return buildingsData.buildings;
        } catch (err) {
            console.error('Failed to fetch buildings:', err);
            return [];
        }
    }, []);

    /**
     * Wyczyść wyniki
     */
    const clearResults = useCallback(() => {
        setState({
            result: null,
            buildings: [],
            isLoading: false,
            error: null,
        });
    }, []);

    return {
        ...state,
        runAnalysis,
        loadDemoData,
        fetchBuildings,
        clearResults,
    };
}
