/**
 * CrisisEye - Dashboard Component
 * Panel ze statystykami analizy + STRATY FINANSOWE + RAPORT
 */

import { motion } from 'framer-motion';
import {
    Droplets,
    Building2,
    AlertTriangle,
    Clock,
    TrendingUp,
    MapPin,
    DollarSign,
    FileText,
    Download
} from 'lucide-react';
import type { AnalysisResponse } from '../../types';

interface DashboardProps {
    result: AnalysisResponse | null;
    isLoading: boolean;
}

interface StatCardProps {
    icon: React.ReactNode;
    label: string;
    value: string | number;
    subvalue?: string;
    color: 'cyan' | 'red' | 'purple' | 'green' | 'yellow';
    delay?: number;
}

// Średnie koszty szkód powodziowych (PLN)
const DAMAGE_COSTS = {
    residential: 150000,    // średni koszt naprawy domu mieszkalnego
    commercial: 500000,     // budynek komercyjny
    industrial: 1200000,    // zakład przemysłowy
    infrastructure: 300000, // infrastruktura (drogi, mosty)
    agricultural: 50000,    // uprawy na km²
};

function StatCard({ icon, label, value, subvalue, color, delay = 0 }: StatCardProps) {
    const colorClasses = {
        cyan: 'text-cyber-cyan border-cyber-cyan/30',
        red: 'text-cyber-red border-cyber-red/30',
        purple: 'text-cyber-purple border-cyber-purple/30',
        green: 'text-cyber-green border-cyber-green/30',
        yellow: 'text-cyber-yellow border-cyber-yellow/30',
    };

    return (
        <motion.div
            className={`card border-l-4 ${colorClasses[color]}`}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay, duration: 0.3 }}
        >
            <div className="flex items-start justify-between">
                <div>
                    <p className="text-sm text-gray-400 mb-1">{label}</p>
                    <p className="stat-number text-2xl">{value}</p>
                    {subvalue && (
                        <p className="text-xs text-gray-500 mt-1">{subvalue}</p>
                    )}
                </div>
                <div className={`p-2 rounded-lg bg-orbital-surface ${colorClasses[color]}`}>
                    {icon}
                </div>
            </div>
        </motion.div>
    );
}

// Funkcja do szacowania strat finansowych
function estimateFinancialLoss(buildingsAffected: number, floodedAreaKm2: number): {
    totalLoss: number;
    buildingDamage: number;
    infrastructureDamage: number;
    agriculturalLoss: number;
} {
    // Zakładamy mix budynków: 70% mieszkalne, 20% komercyjne, 10% przemysłowe
    const residential = Math.floor(buildingsAffected * 0.7);
    const commercial = Math.floor(buildingsAffected * 0.2);
    const industrial = Math.floor(buildingsAffected * 0.1);

    const buildingDamage =
        residential * DAMAGE_COSTS.residential +
        commercial * DAMAGE_COSTS.commercial +
        industrial * DAMAGE_COSTS.industrial;

    // Infrastruktura: ~1 obiekt na 2 km²
    const infrastructureDamage = Math.ceil(floodedAreaKm2 / 2) * DAMAGE_COSTS.infrastructure;

    // Straty rolne: 30% zalanego terenu to uprawy
    const agriculturalLoss = (floodedAreaKm2 * 0.3) * DAMAGE_COSTS.agricultural;

    return {
        totalLoss: buildingDamage + infrastructureDamage + agriculturalLoss,
        buildingDamage,
        infrastructureDamage,
        agriculturalLoss,
    };
}

// Funkcja do generowania raportu
function generateReport(result: AnalysisResponse): string {
    const { stats, buildings_affected, processing_time_seconds } = result;
    if (!stats) return '';

    const losses = estimateFinancialLoss(buildings_affected, stats.flooded_area_km2);
    const date = new Date().toLocaleDateString('pl-PL');
    const time = new Date().toLocaleTimeString('pl-PL');

    return `
╔══════════════════════════════════════════════════════════════╗
║              RAPORT ANALIZY POWODZI - CrisisEye              ║
╠══════════════════════════════════════════════════════════════╣
║ Data wygenerowania: ${date} ${time}
║ Czas przetwarzania: ${processing_time_seconds.toFixed(2)} sekund
╠══════════════════════════════════════════════════════════════╣
║                    ZASIĘG POWODZI                            ║
╠══════════════════════════════════════════════════════════════╣
║ Analizowany obszar:     ${stats.area_km2.toFixed(2)} km²
║ Obszar zalany:          ${stats.flooded_area_km2.toFixed(2)} km²
║ Procent zalania:        ${stats.flood_percentage.toFixed(1)}%
║ Piksele zalane:         ${stats.flooded_pixels.toLocaleString()} / ${stats.total_pixels.toLocaleString()}
╠══════════════════════════════════════════════════════════════╣
║                    STRATY MATERIALNE                         ║
╠══════════════════════════════════════════════════════════════╣
║ Budynki dotknięte:      ${buildings_affected}
║   - Mieszkalne (~70%):  ${Math.floor(buildings_affected * 0.7)}
║   - Komercyjne (~20%):  ${Math.floor(buildings_affected * 0.2)}
║   - Przemysłowe (~10%): ${Math.floor(buildings_affected * 0.1)}
╠══════════════════════════════════════════════════════════════╣
║                 SZACOWANE STRATY FINANSOWE                   ║
╠══════════════════════════════════════════════════════════════╣
║ Szkody budynków:        ${(losses.buildingDamage / 1000000).toFixed(2)} mln PLN
║ Szkody infrastruktury:  ${(losses.infrastructureDamage / 1000000).toFixed(2)} mln PLN
║ Straty rolne:           ${(losses.agriculturalLoss / 1000000).toFixed(2)} mln PLN
║ ─────────────────────────────────────────────────────────────
║ RAZEM:                  ${(losses.totalLoss / 1000000).toFixed(2)} mln PLN
╠══════════════════════════════════════════════════════════════╣
║                      REKOMENDACJE                            ║
╠══════════════════════════════════════════════════════════════╣
║ ${stats.flood_percentage > 30 ? '[!] WYSOKI POZIOM ZAGROZENIA - wymagana natychmiastowa ewakuacja' : stats.flood_percentage > 15 ? '[!] SREDNI POZIOM ZAGROZENIA - monitorowac sytuacje' : '[OK] NISKI POZIOM ZAGROZENIA - standardowe procedury'}
║ 
║ Priorytetowe działania:
║ 1. Ewakuacja ${Math.ceil(buildings_affected * 0.3)} budynków w strefie wysokiego ryzyka
║ 2. Zabezpieczenie ${Math.ceil(stats.flooded_area_km2 * 0.5)} km dróg
║ 3. Uruchomienie pomp o wydajności min. ${Math.ceil(stats.flooded_area_km2 * 1000)} m³/h
╚══════════════════════════════════════════════════════════════╝

Wygenerowano przez CrisisEye
Hackathon "AI miedzy orbitami" 2026
    `.trim();
}

export function Dashboard({ result, isLoading }: DashboardProps) {

    // Funkcja pobierania raportu
    const downloadReport = () => {
        if (!result) return;
        const report = generateReport(result);
        const blob = new Blob([report], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `raport_powodzi_${new Date().toISOString().split('T')[0]}.txt`;
        a.click();
        URL.revokeObjectURL(url);
    };

    if (isLoading) {
        return (
            <div className="glass rounded-xl p-6">
                <div className="flex items-center justify-center gap-3">
                    <motion.div
                        className="w-6 h-6 border-2 border-cyber-cyan border-t-transparent rounded-full"
                        animate={{ rotate: 360 }}
                        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                    />
                    <span className="text-gray-400">Analyzing SAR data...</span>
                </div>
            </div>
        );
    }

    if (!result || !result.stats) {
        return (
            <div className="glass rounded-xl p-6 text-center">
                <Droplets className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                <p className="text-gray-400">
                    Wybierz obszar na mapie i kliknij "Run Analysis" lub "Load Demo Data".
                </p>
            </div>
        );
    }

    const { stats, buildings_affected, processing_time_seconds, status } = result;
    const losses = estimateFinancialLoss(buildings_affected, stats.flooded_area_km2);

    return (
        <div className="space-y-4">
            {/* Status banner */}
            <motion.div
                className={`p-3 rounded-lg flex items-center gap-3 ${status === 'completed'
                    ? 'bg-cyber-green/10 border border-cyber-green/30'
                    : 'bg-cyber-red/10 border border-cyber-red/30'
                    }`}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
            >
                {status === 'completed' ? (
                    <>
                        <TrendingUp className="w-5 h-5 text-cyber-green" />
                        <span className="text-cyber-green font-medium">Analiza zakończona</span>
                    </>
                ) : (
                    <>
                        <AlertTriangle className="w-5 h-5 text-cyber-red" />
                        <span className="text-cyber-red font-medium">Błąd analizy</span>
                    </>
                )}
                <span className="text-gray-400 text-sm ml-auto">
                    <Clock className="w-4 h-4 inline mr-1" />
                    {processing_time_seconds.toFixed(2)}s
                </span>
            </motion.div>

            {/* Stats grid */}
            <div className="grid grid-cols-2 gap-4">
                <StatCard
                    icon={<Droplets className="w-5 h-5" />}
                    label="Obszar zalany"
                    value={`${stats.flooded_area_km2.toFixed(2)}`}
                    subvalue="km²"
                    color="cyan"
                    delay={0.1}
                />

                <StatCard
                    icon={<MapPin className="w-5 h-5" />}
                    label="Całkowity obszar"
                    value={`${stats.area_km2.toFixed(2)}`}
                    subvalue="km²"
                    color="purple"
                    delay={0.2}
                />

                <StatCard
                    icon={<AlertTriangle className="w-5 h-5" />}
                    label="Procent zalania"
                    value={`${stats.flood_percentage.toFixed(1)}%`}
                    subvalue="analizowanego terenu"
                    color={stats.flood_percentage > 20 ? 'red' : 'yellow'}
                    delay={0.3}
                />

                <StatCard
                    icon={<Building2 className="w-5 h-5" />}
                    label="Budynki zagrożone"
                    value={buildings_affected}
                    subvalue="obiektów"
                    color="red"
                    delay={0.4}
                />
            </div>

            {/* 💰 STRATY FINANSOWE */}
            <motion.div
                className="card border-l-4 border-cyber-yellow/50 bg-gradient-to-r from-cyber-yellow/5 to-transparent"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
            >
                <div className="flex items-center gap-2 mb-3">
                    <DollarSign className="w-5 h-5 text-cyber-yellow" />
                    <h4 className="font-semibold text-cyber-yellow">Szacowane straty finansowe</h4>
                </div>
                <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                        <span className="text-gray-400">Budynki mieszkalne:</span>
                        <span className="text-gray-200 font-mono">
                            {(losses.buildingDamage * 0.7 / 1000000).toFixed(2)} mln PLN
                        </span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-400">Budynki komercyjne:</span>
                        <span className="text-gray-200 font-mono">
                            {(losses.buildingDamage * 0.3 / 1000000).toFixed(2)} mln PLN
                        </span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-400">Infrastruktura:</span>
                        <span className="text-gray-200 font-mono">
                            {(losses.infrastructureDamage / 1000000).toFixed(2)} mln PLN
                        </span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-400">Straty rolne:</span>
                        <span className="text-gray-200 font-mono">
                            {(losses.agriculturalLoss / 1000000).toFixed(2)} mln PLN
                        </span>
                    </div>
                    <div className="flex justify-between pt-2 border-t border-orbital-border">
                        <span className="text-white font-semibold">RAZEM:</span>
                        <span className="text-cyber-red font-bold text-lg font-mono">
                            {(losses.totalLoss / 1000000).toFixed(2)} mln PLN
                        </span>
                    </div>
                </div>
            </motion.div>

            {/* 📊 RAPORT */}
            <motion.div
                className="card"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 }}
            >
                <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                        <FileText className="w-5 h-5 text-cyber-cyan" />
                        <h4 className="font-semibold text-white">Raport o powodzi</h4>
                    </div>
                    <motion.button
                        onClick={downloadReport}
                        className="flex items-center gap-2 px-3 py-1.5 bg-cyber-cyan/20 text-cyber-cyan rounded-lg hover:bg-cyber-cyan/30 transition-colors"
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                    >
                        <Download className="w-4 h-4" />
                        <span className="text-sm">Pobierz raport</span>
                    </motion.button>
                </div>
                <div className="text-xs text-gray-400 space-y-1">
                    <p>• Pełna analiza zasięgu powodzi</p>
                    <p>• Szczegółowe szacunki strat</p>
                    <p>• Rekomendacje działań</p>
                    <p>• Format TXT gotowy do wydruku</p>
                </div>
            </motion.div>

            {/* Alert - poziom zagrożenia */}
            <motion.div
                className={`p-4 rounded-lg ${stats.flood_percentage > 30
                    ? 'bg-cyber-red/20 border border-cyber-red/50'
                    : stats.flood_percentage > 15
                        ? 'bg-cyber-yellow/20 border border-cyber-yellow/50'
                        : 'bg-cyber-green/20 border border-cyber-green/50'
                    }`}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.7 }}
            >
                <div className="flex items-center gap-2 mb-2">
                    <AlertTriangle className={`w-5 h-5 ${stats.flood_percentage > 30
                        ? 'text-cyber-red'
                        : stats.flood_percentage > 15
                            ? 'text-cyber-yellow'
                            : 'text-cyber-green'
                        }`} />
                    <span className={`font-semibold ${stats.flood_percentage > 30
                        ? 'text-cyber-red'
                        : stats.flood_percentage > 15
                            ? 'text-cyber-yellow'
                            : 'text-cyber-green'
                        }`}>
                        {stats.flood_percentage > 30
                            ? 'WYSOKI POZIOM ZAGROZENIA'
                            : stats.flood_percentage > 15
                                ? 'SREDNI POZIOM ZAGROZENIA'
                                : 'NISKI POZIOM ZAGROZENIA'
                        }
                    </span>
                </div>
                <p className="text-sm text-gray-300">
                    {stats.flood_percentage > 30
                        ? `Wymagana natychmiastowa ewakuacja ${Math.ceil(buildings_affected * 0.5)} budynków. Uruchomić procedury kryzysowe.`
                        : stats.flood_percentage > 15
                            ? `Monitorować sytuację. Przygotować ewakuację ${Math.ceil(buildings_affected * 0.2)} budynków w strefie ryzyka.`
                            : 'Sytuacja pod kontrolą. Kontynuować standardowe procedury monitoringu.'
                    }
                </p>
            </motion.div>
        </div>
    );
}
