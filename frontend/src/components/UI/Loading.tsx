/**
 * CrisisEye - Loading Component
 * Animowany spinner ładowania
 */

import { motion } from 'framer-motion';
import { Satellite } from 'lucide-react';

interface LoadingProps {
    text?: string;
    size?: 'sm' | 'md' | 'lg';
}

export function Loading({ text = 'Loading...', size = 'md' }: LoadingProps) {
    const sizes = {
        sm: { icon: 'w-6 h-6', text: 'text-sm' },
        md: { icon: 'w-10 h-10', text: 'text-base' },
        lg: { icon: 'w-16 h-16', text: 'text-lg' },
    };

    return (
        <div className="flex flex-col items-center justify-center gap-4">
            <motion.div
                className="relative"
                animate={{ rotate: 360 }}
                transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
            >
                <Satellite className={`${sizes[size].icon} text-cyber-cyan`} />
                <motion.div
                    className="absolute inset-0 rounded-full border-2 border-cyber-cyan/50"
                    animate={{ scale: [1, 1.5, 1], opacity: [0.5, 0, 0.5] }}
                    transition={{ duration: 2, repeat: Infinity }}
                />
            </motion.div>
            <motion.p
                className={`${sizes[size].text} text-gray-400`}
                animate={{ opacity: [0.5, 1, 0.5] }}
                transition={{ duration: 1.5, repeat: Infinity }}
            >
                {text}
            </motion.p>
        </div>
    );
}

/**
 * Full screen loading overlay
 */
export function LoadingOverlay({ text }: { text?: string }) {
    return (
        <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center bg-orbital-bg/80 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
        >
            <Loading text={text} size="lg" />
        </motion.div>
    );
}
