/**
 * CrisisEye - Header Component
 * Górny pasek nawigacyjny z logiem i statusem
 */

import { motion } from "framer-motion";
import { Satellite, Activity, AlertTriangle } from "lucide-react";

interface HeaderProps {
  isConnected: boolean;
  isAnalyzing: boolean;
}

export function Header({ isConnected, isAnalyzing }: HeaderProps) {
  return (
    <motion.header
      className="glass-dark fixed top-0 left-0 right-0 z-50 h-16"
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      transition={{ type: "spring", stiffness: 100 }}
    >
      <div className="h-full flex items-center justify-between px-6">
        {/* Logo */}
        <div className="flex items-center gap-3">
          <motion.div
            className="relative"
            animate={{ rotate: isAnalyzing ? 360 : 0 }}
            transition={{
              duration: 2,
              repeat: isAnalyzing ? Infinity : 0,
              ease: "linear",
            }}
          >
            <Satellite className="w-8 h-8 text-cyber-cyan" />
            {isAnalyzing && (
              <motion.div
                className="absolute inset-0 rounded-full border-2 border-cyber-cyan"
                animate={{ scale: [1, 1.5], opacity: [1, 0] }}
                transition={{ duration: 1, repeat: Infinity }}
              />
            )}
          </motion.div>
          <div>
            <h1 className="text-xl font-bold text-white">
              Crisis<span className="text-cyber-cyan">Eye</span>
            </h1>
            <p className="text-xs text-gray-500">Flood Detection System</p>
          </div>
        </div>

        {/* Status indicators */}
        <div className="flex items-center gap-6">
          {/* Analysis Status */}
          {isAnalyzing && (
            <motion.div
              className="flex items-center gap-2 px-3 py-1 bg-cyber-cyan/10 rounded-full"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
            >
              <motion.div
                className="w-2 h-2 rounded-full bg-cyber-cyan"
                animate={{ opacity: [1, 0.3, 1] }}
                transition={{ duration: 1, repeat: Infinity }}
              />
              <span className="text-sm text-cyber-cyan font-medium">
                Analizowanie...
              </span>
            </motion.div>
          )}

          {/* Connection Status */}
          <div className="flex items-center gap-2">
            <Activity
              className={`w-4 h-4 ${
                isConnected ? "text-cyber-green" : "text-cyber-red"
              }`}
            />
            <span
              className={`text-sm ${
                isConnected ? "text-cyber-green" : "text-cyber-red"
              }`}
            >
              {isConnected ? "Połączono" : "Rozłączono"}
            </span>
          </div>
        </div>
      </div>
    </motion.header>
  );
}
