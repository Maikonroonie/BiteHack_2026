/**
 * CrisisEye - Main App Component
 * Główny komponent aplikacji łączący wszystkie elementy
 */

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Header } from './components/Layout/Header';
import { Sidebar } from './components/Layout/Sidebar';
import { Dashboard } from './components/Dashboard/Dashboard';
import { Loading } from './components/UI/Loading';
import { useFloodData } from './hooks/useFloodData';
import { checkHealth } from './services/api';
import type { AnalysisRequest, BoundingBox, FloodGeoJSON } from './types';

// Dynamically import map components to avoid SSR issues
import { MapContainer, TileLayer, GeoJSON, FeatureGroup, Rectangle, useMapEvents } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

// Fix Leaflet icon issue
import L from 'leaflet';
import iconUrl from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

const DefaultIcon = L.icon({
    iconUrl,
    shadowUrl: iconShadow,
    iconSize: [25, 41],
    iconAnchor: [12, 41],
});
L.Marker.prototype.options.icon = DefaultIcon;

// Rectangle selector component
function RectangleSelector({ onSelect }: { onSelect: (bbox: BoundingBox) => void }) {
    const [drawing, setDrawing] = useState(false);
    const [startPoint, setStartPoint] = useState<L.LatLng | null>(null);
    const [bounds, setBounds] = useState<L.LatLngBounds | null>(null);

    useMapEvents({
        mousedown(e) {
            if (e.originalEvent.shiftKey) {
                setDrawing(true);
                setStartPoint(e.latlng);
                setBounds(null);
            }
        },
        mousemove(e) {
            if (drawing && startPoint) {
                setBounds(L.latLngBounds(startPoint, e.latlng));
            }
        },
        mouseup(e) {
            if (drawing && startPoint) {
                const finalBounds = L.latLngBounds(startPoint, e.latlng);
                setDrawing(false);
                setStartPoint(null);
                setBounds(finalBounds);

                onSelect({
                    min_lon: finalBounds.getWest(),
                    min_lat: finalBounds.getSouth(),
                    max_lon: finalBounds.getEast(),
                    max_lat: finalBounds.getNorth(),
                });
            }
        },
    });

    if (!bounds) return null;

    return (
        <Rectangle
            bounds={bounds}
            pathOptions={{
                color: '#00d4ff',
                weight: 2,
                fillColor: '#00d4ff',
                fillOpacity: 0.2,
            }}
        />
    );
}

// Flood layer component
function FloodOverlay({ data }: { data: FloodGeoJSON }) {
    const getStyle = (feature: any) => {
        const probability = feature?.properties?.flood_probability || 0;
        const hue = (1 - probability) * 200;
        return {
            fillColor: `hsl(${hue}, 80%, 50%)`,
            fillOpacity: 0.5 + probability * 0.3,
            color: 'rgba(0, 212, 255, 0.8)',
            weight: 1,
        };
    };

    return (
        <GeoJSON
            key={JSON.stringify(data)}
            data={data as any}
            style={getStyle}
            onEachFeature={(feature, layer) => {
                const props = feature.properties;
                layer.bindPopup(`
          <div style="font-family: monospace;">
            <strong>Flood Risk: ${((props.flood_probability || 0) * 100).toFixed(0)}%</strong>
          </div>
        `);
            }}
        />
    );
}

export default function App() {
    const [isConnected, setIsConnected] = useState(false);
    const [selectedBbox, setSelectedBbox] = useState<BoundingBox | null>(null);
    const { result, buildings, isLoading, error, runAnalysis, loadDemoData, clearResults } = useFloodData();

    // Check backend connection
    useEffect(() => {
        const checkConnection = async () => {
            try {
                await checkHealth();
                setIsConnected(true);
            } catch {
                setIsConnected(false);
            }
        };

        checkConnection();
        const interval = setInterval(checkConnection, 30000);
        return () => clearInterval(interval);
    }, []);

    // Handle analysis request
    const handleAnalyze = useCallback(async (request: AnalysisRequest) => {
        try {
            await runAnalysis(request);
        } catch (err) {
            console.error('Analysis failed:', err);
        }
    }, [runAnalysis]);

    // Handle demo data load
    const handleLoadDemo = useCallback(async () => {
        try {
            await loadDemoData();
            // Set demo bbox for Wrocław
            setSelectedBbox({
                min_lon: 17.0,
                min_lat: 51.08,
                max_lon: 17.1,
                max_lat: 51.13,
            });
        } catch (err) {
            console.error('Failed to load demo:', err);
        }
    }, [loadDemoData]);

    return (
        <div className="min-h-screen bg-orbital-bg bg-grid">
            {/* Header */}
            <Header isConnected={isConnected} isAnalyzing={isLoading} />

            {/* Sidebar */}
            <Sidebar
                onAnalyze={handleAnalyze}
                onLoadDemo={handleLoadDemo}
                isLoading={isLoading}
                selectedBbox={selectedBbox}
            />

            {/* Main Content */}
            <main className="ml-[320px] pt-16 p-6 min-h-screen">
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-112px)]">
                    {/* Map - 2/3 width */}
                    <motion.div
                        className="lg:col-span-2 h-full"
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.2 }}
                    >
                        <div className="h-full rounded-xl overflow-hidden border border-orbital-border relative">
                            <MapContainer
                                center={[51.1, 17.03]}
                                zoom={12}
                                className="h-full w-full"
                                style={{ background: '#12121a' }}
                            >
                                <TileLayer
                                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                                />

                                {/* Selection rectangle */}
                                <RectangleSelector onSelect={setSelectedBbox} />

                                {/* Selected area display */}
                                {selectedBbox && (
                                    <Rectangle
                                        bounds={[
                                            [selectedBbox.min_lat, selectedBbox.min_lon],
                                            [selectedBbox.max_lat, selectedBbox.max_lon],
                                        ]}
                                        pathOptions={{
                                            color: '#00d4ff',
                                            weight: 2,
                                            fillColor: '#00d4ff',
                                            fillOpacity: 0.1,
                                            dashArray: '5, 5',
                                        }}
                                    />
                                )}

                                {/* Flood overlay */}
                                {result?.flood_geojson && (
                                    <FloodOverlay data={result.flood_geojson} />
                                )}
                            </MapContainer>

                            {/* Map instructions overlay */}
                            <div className="absolute bottom-4 left-4 glass px-3 py-2 rounded-lg z-[1000]">
                                <p className="text-xs text-gray-400">
                                    <kbd className="px-1 py-0.5 bg-orbital-surface rounded text-cyber-cyan">Shift</kbd>
                                    {' + drag to select area'}
                                </p>
                            </div>
                        </div>
                    </motion.div>

                    {/* Dashboard - 1/3 width */}
                    <motion.div
                        className="h-full overflow-y-auto"
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.3 }}
                    >
                        <div className="space-y-6">
                            {/* Title */}
                            <div>
                                <h2 className="text-xl font-semibold text-white">Analysis Results</h2>
                                <p className="text-sm text-gray-500">Flood detection statistics</p>
                            </div>

                            {/* Dashboard */}
                            <Dashboard result={result} isLoading={isLoading} />

                            {/* Error display */}
                            <AnimatePresence>
                                {error && (
                                    <motion.div
                                        className="p-4 bg-cyber-red/10 border border-cyber-red/30 rounded-lg"
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        exit={{ opacity: 0, y: -10 }}
                                    >
                                        <p className="text-cyber-red text-sm">{error}</p>
                                    </motion.div>
                                )}
                            </AnimatePresence>

                            {/* Connection status warning */}
                            {!isConnected && (
                                <motion.div
                                    className="p-4 bg-cyber-yellow/10 border border-cyber-yellow/30 rounded-lg"
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                >
                                    <p className="text-cyber-yellow text-sm">
                                        ⚠️ Backend not connected. Start the server with:
                                    </p>
                                    <code className="block mt-2 text-xs bg-orbital-surface p-2 rounded font-mono text-gray-300">
                                        cd backend && uvicorn main:app --reload
                                    </code>
                                </motion.div>
                            )}
                        </div>
                    </motion.div>
                </div>
            </main>
        </div>
    );
}
