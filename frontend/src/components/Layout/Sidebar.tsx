/**
 * CrisisEye - Sidebar Component (Polish Version)
 * Panel boczny z formularzem analizy i predykcji
 */

import { useState } from "react";
import { motion } from "framer-motion";
import {
  MapPin,
  Calendar,
  Radio,
  Play,
  RotateCcw,
  Layers,
  Clock,
  Zap,
} from "lucide-react";
import type {
  AnalysisRequest,
  BoundingBox,
  PredictionRequest,
} from "../../types";

interface SidebarProps {
  onAnalyze: (request: AnalysisRequest) => void;
  onPredict: (request: PredictionRequest) => void;
  onLoadDemo: () => void;
  onLoadPredictionDemo: () => void;
  isLoading: boolean;
  selectedBbox: BoundingBox | null;
}

type Mode = "analysis" | "prediction";

export function Sidebar({
  onAnalyze,
  onPredict,
  onLoadDemo,
  onLoadPredictionDemo,
  isLoading,
  selectedBbox,
}: SidebarProps) {
  const [mode, setMode] = useState<Mode>("prediction");
  const [dateBefore, setDateBefore] = useState("2024-01-01");
  const [dateAfter, setDateAfter] = useState("2024-01-15");
  const [polarization, setPolarization] = useState<"VV" | "VH">("VV");
  const [predictionHours, setPredictionHours] = useState(6);
  const [isExpanded] = useState(true);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!selectedBbox) {
      alert("Proszę zaznaczyć obszar na mapie (Shift + Przeciągnij).");
      return;
    }

    if (mode === "prediction") {
      onPredict({
        bbox: selectedBbox,
        prediction_hours: predictionHours,
      });
    } else {
      onAnalyze({
        bbox: selectedBbox,
        date_before: dateBefore,
        date_after: dateAfter,
        polarization,
      });
    }
  };

  return (
    <motion.aside
      className="glass fixed left-0 top-16 bottom-0 z-40 overflow-hidden"
      initial={{ width: 0 }}
      animate={{ width: isExpanded ? 320 : 64 }}
      transition={{ type: "spring", stiffness: 100 }}
    >
      <div className="h-full flex flex-col p-4 overflow-y-auto">
        {/* Przełącznik Trybu */}
        <div className="mb-4">
          <div className="flex rounded-lg bg-orbital-surface p-1">
            <button
              onClick={() => setMode("prediction")}
              className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-md text-sm font-medium transition-all ${
                mode === "prediction"
                  ? "bg-cyber-cyan text-orbital-bg"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              <Zap className="w-4 h-4" />
              Predykcja
            </button>
            <button
              onClick={() => setMode("analysis")}
              className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-md text-sm font-medium transition-all ${
                mode === "analysis"
                  ? "bg-cyber-cyan text-orbital-bg"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              <Layers className="w-4 h-4" />
              Analiza SAR
            </button>
          </div>
        </div>

        {/* Nagłówek Sekcji */}
        <div className="space-y-6">
          <div className="flex items-center gap-2 text-cyber-cyan">
            {mode === "prediction" ? (
              <Zap className="w-5 h-5" />
            ) : (
              <Layers className="w-5 h-5" />
            )}
            <h2 className="font-semibold">
              {mode === "prediction"
                ? "Prognoza Krótkoterminowa"
                : "Analiza Satelitarna"}
            </h2>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Wybór Obszaru */}
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-sm text-gray-400">
                <MapPin className="w-4 h-4" />
                Wybrany obszar
              </label>
              <div className="p-3 bg-orbital-surface rounded-lg border border-orbital-border">
                {selectedBbox ? (
                  <div className="text-xs font-mono text-gray-300 space-y-1">
                    <div>
                      SW: {selectedBbox.min_lat.toFixed(4)},{" "}
                      {selectedBbox.min_lon.toFixed(4)}
                    </div>
                    <div>
                      NE: {selectedBbox.max_lat.toFixed(4)},{" "}
                      {selectedBbox.max_lon.toFixed(4)}
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-gray-500 italic">
                    Przytrzymaj SHIFT i zaznacz obszar na mapie...
                  </p>
                )}
              </div>
            </div>

            {mode === "prediction" ? (
              /* Tryb Predykcji */
              <>
                <div className="space-y-2">
                  <label className="flex items-center justify-between text-sm text-gray-400">
                    <span className="flex items-center gap-2">
                      <Clock className="w-4 h-4" />
                      Horyzont czasowy
                    </span>
                    <span className="text-cyber-cyan font-bold">
                      +{predictionHours}h
                    </span>
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="24"
                    value={predictionHours}
                    onChange={(e) =>
                      setPredictionHours(parseInt(e.target.value))
                    }
                    className="w-full h-2 bg-orbital-surface rounded-lg appearance-none cursor-pointer accent-cyber-cyan"
                  />
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>1h</span>
                    <span>12h</span>
                    <span>24h</span>
                  </div>
                </div>
              </>
            ) : (
              /* Tryb Analizy SAR */
              <>
                {/* Data Przed */}
                <div className="space-y-2">
                  <label className="flex items-center gap-2 text-sm text-gray-400">
                    <Calendar className="w-4 h-4" />
                    Data przed powodzią
                  </label>
                  <input
                    type="date"
                    value={dateBefore}
                    onChange={(e) => setDateBefore(e.target.value)}
                    className="input"
                  />
                </div>

                {/* Data Po */}
                <div className="space-y-2">
                  <label className="flex items-center gap-2 text-sm text-gray-400">
                    <Calendar className="w-4 h-4" />
                    Data w trakcie/po
                  </label>
                  <input
                    type="date"
                    value={dateAfter}
                    onChange={(e) => setDateAfter(e.target.value)}
                    className="input"
                  />
                </div>

                {/* Polaryzacja */}
                <div className="space-y-2">
                  <label className="flex items-center gap-2 text-sm text-gray-400">
                    <Radio className="w-4 h-4" />
                    Polaryzacja SAR
                  </label>
                  <div className="flex gap-2">
                    {(["VV", "VH"] as const).map((pol) => (
                      <button
                        key={pol}
                        type="button"
                        onClick={() => setPolarization(pol)}
                        className={`flex-1 py-2 rounded-lg font-medium transition-all ${
                          polarization === pol
                            ? "bg-cyber-cyan text-orbital-bg"
                            : "bg-orbital-surface border border-orbital-border text-gray-300 hover:border-cyber-cyan"
                        }`}
                      >
                        {pol}
                      </button>
                    ))}
                  </div>
                </div>
              </>
            )}

            {/* Przycisk Akcji */}
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
                    transition={{
                      duration: 1,
                      repeat: Infinity,
                      ease: "linear",
                    }}
                  />
                  {mode === "prediction"
                    ? "Przetwarzanie..."
                    : "Analizowanie..."}
                </>
              ) : (
                <>
                  <Play className="w-5 h-5" />
                  {mode === "prediction"
                    ? `Przewiduj za ${predictionHours}h`
                    : "Rozpocznij analizę"}
                </>
              )}
            </motion.button>
          </form>

          {/* Przycisk Demo */}
          <div className="pt-4 border-t border-orbital-border">
            <motion.button
              onClick={
                mode === "prediction" ? onLoadPredictionDemo : onLoadDemo
              }
              disabled={isLoading}
              className="w-full btn-secondary flex items-center justify-center gap-2"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <RotateCcw className="w-4 h-4" />
              Wczytaj Demo
            </motion.button>
            <p className="text-xs text-gray-500 mt-2 text-center">
              {mode === "prediction"
                ? "Wrocław - Symulacja opadu (Demo)"
                : "Wrocław 1997 - Dane historyczne"}
            </p>
          </div>
        </div>
      </div>
    </motion.aside>
  );
}
