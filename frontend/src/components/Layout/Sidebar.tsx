/**
 * CrisisEye - Sidebar Component
 * Panel boczny z formularzem analizy i nawigacją
 */

import { useState } from 'react';
import { motion } from 'framer-motion';
import {
    MapPin,
    Calendar,
    Radio,
    Play,
    RotateCcw,
    ChevronRight,
    Layers,
    Building2,
    Waves
} from 'lucide-react';
import type { AnalysisRequest, BoundingBox } from '../../types';

interface SidebarProps {
    onAnalyze: (request: AnalysisRequest) => void;
    onLoadDemo: () => void;
    isLoading: boolean;
    selectedBbox: BoundingBox | null;
}

export function Sidebar({ onAnalyze, onLoadDemo, isLoading, selectedBbox }: SidebarProps) {
    const [dateBefore, setDateBefore] = useState('2024-01-01');
    const [dateAfter, setDateAfter] = useState('2024-01-15');
    const [polarization, setPolarization] = useState<'VV' | 'VH'>('VV');
    const [isExpanded] = useState(true);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();

        if (!selectedBbox) {
            alert('Zaznacz obszar na mapie!');
            return;
        }

        onAnalyze({
            bbox: selectedBbox,
            date_before: dateBefore,
            date_after: dateAfter,
            polarization,
        });
    };

    return (
        <motion.aside
            className="glass fixed left-0 top-16 bottom-0 z-40 overflow-hidden"
            initial={{ width: 0 }}
            animate={{ width: isExpanded ? 320 : 64 }}
            transition={{ type: 'spring', stiffness: 100 }}
        >
            <div className="h-full flex flex-col p-4 overflow-y-auto">
                {/* Analysis Form */}
                <div className="space-y-6">
                    <div className="flex items-center gap-2 text-cyber-cyan">
                        <Layers className="w-5 h-5" />
                        <h2 className="font-semibold">Flood Analysis</h2>
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-4">
                        {/* Bounding Box Display */}
                        <div className="space-y-2">
                            <label className="flex items-center gap-2 text-sm text-gray-400">
                                <MapPin className="w-4 h-4" />
                                Selected Area
                            </label>
                            <div className="p-3 bg-orbital-surface rounded-lg border border-orbital-border">
                                {selectedBbox ? (
                                    <div className="text-xs font-mono text-gray-300 space-y-1">
                                        <div>SW: {selectedBbox.min_lat.toFixed(4)}, {selectedBbox.min_lon.toFixed(4)}</div>
                                        <div>NE: {selectedBbox.max_lat.toFixed(4)}, {selectedBbox.max_lon.toFixed(4)}</div>
                                    </div>
                                ) : (
                                    <p className="text-sm text-gray-500 italic">
                                        Draw rectangle on map...
                                    </p>
                                )}
                            </div>
                        </div>

                        {/* Date Before */}
                        <div className="space-y-2">
                            <label className="flex items-center gap-2 text-sm text-gray-400">
                                <Calendar className="w-4 h-4" />
                                Date Before Flood
                            </label>
                            <input
                                type="date"
                                value={dateBefore}
                                onChange={(e) => setDateBefore(e.target.value)}
                                className="input"
                            />
                        </div>

                        {/* Date After */}
                        <div className="space-y-2">
                            <label className="flex items-center gap-2 text-sm text-gray-400">
                                <Calendar className="w-4 h-4" />
                                Date After Flood
                            </label>
                            <input
                                type="date"
                                value={dateAfter}
                                onChange={(e) => setDateAfter(e.target.value)}
                                className="input"
                            />
                        </div>

                        {/* Polarization */}
                        <div className="space-y-2">
                            <label className="flex items-center gap-2 text-sm text-gray-400">
                                <Radio className="w-4 h-4" />
                                SAR Polarization
                            </label>
                            <div className="flex gap-2">
                                {(['VV', 'VH'] as const).map((pol) => (
                                    <button
                                        key={pol}
                                        type="button"
                                        onClick={() => setPolarization(pol)}
                                        className={`flex-1 py-2 rounded-lg font-medium transition-all ${polarization === pol
                                                ? 'bg-cyber-cyan text-orbital-bg'
                                                : 'bg-orbital-surface border border-orbital-border text-gray-300 hover:border-cyber-cyan'
                                            }`}
                                    >
                                        {pol}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Submit Button */}
                        <motion.button
                            type="submit"
                            disabled={isLoading || !selectedBbox}
                            className="w-full btn-primary flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                        >
                            {isLoading ? (
                                <>
                                    <motion.div
                                        className="w-5 h-5 border-2 border-orbital-bg border-t-transparent rounded-full"
                                        animate={{ rotate: 360 }}
                                        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                                    />
                                    Processing...
                                </>
                            ) : (
                                <>
                                    <Play className="w-5 h-5" />
                                    Run Analysis
                                </>
                            )}
                        </motion.button>
                    </form>

                    {/* Demo Button */}
                    <div className="pt-4 border-t border-orbital-border">
                        <motion.button
                            onClick={onLoadDemo}
                            disabled={isLoading}
                            className="w-full btn-secondary flex items-center justify-center gap-2"
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                        >
                            <RotateCcw className="w-4 h-4" />
                            Load Demo Data
                        </motion.button>
                        <p className="text-xs text-gray-500 mt-2 text-center">
                            Wrocław 1997 flood simulation
                        </p>
                    </div>
                </div>

                {/* Quick Layers */}
                <div className="mt-8 pt-6 border-t border-orbital-border">
                    <h3 className="text-sm font-medium text-gray-400 mb-3">Layers</h3>
                    <div className="space-y-2">
                        {[
                            { icon: Waves, label: 'Flood Mask', active: true },
                            { icon: Building2, label: 'Buildings', active: true },
                            { icon: MapPin, label: 'Infrastructure', active: false },
                        ].map((layer, i) => (
                            <motion.button
                                key={i}
                                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${layer.active
                                        ? 'bg-orbital-surface text-cyber-cyan'
                                        : 'text-gray-500 hover:text-gray-300 hover:bg-orbital-surface/50'
                                    }`}
                                whileHover={{ x: 4 }}
                            >
                                <layer.icon className="w-4 h-4" />
                                <span className="text-sm">{layer.label}</span>
                                <ChevronRight className="w-4 h-4 ml-auto" />
                            </motion.button>
                        ))}
                    </div>
                </div>
            </div>
        </motion.aside>
    );
}
