/**
 * CrisisEye - Evacuation Panel Component
 * Lista priorytetów ewakuacji dla Szefa Sztabu
 */

import { motion } from 'framer-motion';
import type { EvacuationPriority, PredictionResponse } from '../../types';

interface EvacuationPanelProps {
    prediction: PredictionResponse | null;
    isLoading: boolean;
}

const riskColors = {
    critical: 'bg-red-500',
    high: 'bg-orange-500',
    medium: 'bg-yellow-500',
    low: 'bg-green-500',
};

const riskBorderColors = {
    critical: 'border-red-500',
    high: 'border-orange-500',
    medium: 'border-yellow-500',
    low: 'border-green-500',
};

const buildingIcons: Record<string, string> = {
    hospital: '🏥',
    school: '🏫',
    kindergarten: '👶',
    apartments: '🏢',
    residential: '🏠',
    commercial: '🏪',
    industrial: '🏭',
};

export function EvacuationPanel({ prediction, isLoading }: EvacuationPanelProps) {
    if (isLoading) {
        return (
            <div className="glass rounded-xl p-4">
                <div className="animate-pulse space-y-3">
                    <div className="h-4 bg-orbital-surface rounded w-3/4"></div>
                    <div className="h-20 bg-orbital-surface rounded"></div>
                    <div className="h-20 bg-orbital-surface rounded"></div>
                </div>
            </div>
        );
    }

    if (!prediction) {
        return (
            <div className="glass rounded-xl p-4">
                <h3 className="text-lg font-semibold text-white mb-2">🚨 Priorytety Ewakuacji</h3>
                <p className="text-sm text-gray-400">
                    Uruchom predykcję, aby zobaczyć listę budynków do ewakuacji
                </p>
            </div>
        );
    }

    const priorities = prediction.evacuation_priorities || [];

    return (
        <div className="glass rounded-xl p-4">
            {/* Header z podsumowaniem ryzyka */}
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white">🚨 Priorytety Ewakuacji</h3>
                <span className={`px-2 py-1 rounded text-xs font-bold ${prediction.risk_level === 'critical' ? 'bg-red-500 text-white' :
                        prediction.risk_level === 'high' ? 'bg-orange-500 text-white' :
                            prediction.risk_level === 'moderate' ? 'bg-yellow-500 text-black' :
                                'bg-green-500 text-white'
                    }`}>
                    {prediction.risk_level.toUpperCase()}
                </span>
            </div>

            {/* Główne statystyki */}
            <div className="grid grid-cols-2 gap-3 mb-4">
                <div className="bg-orbital-surface rounded-lg p-3">
                    <div className="text-2xl font-bold text-cyber-cyan">
                        {Math.round(prediction.flood_probability * 100)}%
                    </div>
                    <div className="text-xs text-gray-400">Ryzyko za {prediction.prediction_hours}h</div>
                </div>
                <div className="bg-orbital-surface rounded-lg p-3">
                    <div className="text-2xl font-bold text-cyber-cyan">
                        {priorities.length}
                    </div>
                    <div className="text-xs text-gray-400">Budynków zagrożonych</div>
                </div>
            </div>

            {/* Dane o opadach */}
            {prediction.precipitation && (
                <div className="bg-orbital-surface rounded-lg p-3 mb-4">
                    <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-400">💧 Opady (ostatnie 3h)</span>
                        <span className="text-sm font-semibold text-white">
                            {prediction.precipitation.mean_mm.toFixed(1)} mm
                        </span>
                    </div>
                    <div className="flex items-center justify-between mt-1">
                        <span className="text-xs text-gray-500">
                            {prediction.precipitation.is_simulated ? '⚠️ Symulowane' : '🛰️ NASA GPM'}
                        </span>
                        <span className="text-xs text-gray-500">
                            max: {prediction.precipitation.max_mm.toFixed(1)} mm
                        </span>
                    </div>
                </div>
            )}

            {/* Lista budynków do ewakuacji */}
            <div className="space-y-2 max-h-[400px] overflow-y-auto">
                {priorities.length === 0 ? (
                    <p className="text-sm text-gray-400 text-center py-4">
                        Brak budynków wymagających ewakuacji
                    </p>
                ) : (
                    priorities.map((building, index) => (
                        <motion.div
                            key={building.osm_id}
                            className={`bg-orbital-surface rounded-lg p-3 border-l-4 ${riskBorderColors[building.risk_level]}`}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: index * 0.05 }}
                        >
                            <div className="flex items-start justify-between">
                                <div className="flex items-center gap-2">
                                    <span className="text-xl">
                                        {buildingIcons[building.building_type] || '🏛️'}
                                    </span>
                                    <div>
                                        <div className="text-sm font-medium text-white">
                                            {building.name || `Budynek ${building.building_type}`}
                                        </div>
                                        <div className="text-xs text-gray-400">
                                            {building.building_type} • {building.people_estimate} osób
                                        </div>
                                    </div>
                                </div>
                                <div className={`px-2 py-0.5 rounded text-xs font-bold ${riskColors[building.risk_level]} text-white`}>
                                    {Math.round(building.flood_probability * 100)}%
                                </div>
                            </div>
                            <div className="mt-2 flex items-center justify-between text-xs text-gray-500">
                                <span>⏱️ ~{building.estimated_time_to_flood_hours.toFixed(1)}h do zalania</span>
                                <span>📍 {building.lat.toFixed(4)}, {building.lon.toFixed(4)}</span>
                            </div>
                        </motion.div>
                    ))
                )}
            </div>

            {/* Footer z timestamp */}
            <div className="mt-4 pt-3 border-t border-orbital-border">
                <div className="flex items-center justify-between text-xs text-gray-500">
                    <span>Aktualizacja za {prediction.next_update_minutes} min</span>
                    <span>Czas przetwarzania: {prediction.processing_time_seconds.toFixed(2)}s</span>
                </div>
            </div>
        </div>
    );
}
