/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                // Orbital Command Theme
                'orbital': {
                    'bg': '#0a0a0f',
                    'surface': '#12121a',
                    'card': '#1a1a24',
                    'border': '#2a2a3a',
                },
                'cyber': {
                    'cyan': '#00d4ff',
                    'cyan-dark': '#00a8cc',
                    'red': '#ff3b3b',
                    'red-dark': '#cc2e2e',
                    'purple': '#7c3aed',
                    'green': '#10b981',
                    'yellow': '#f59e0b',
                }
            },
            fontFamily: {
                'sans': ['Inter', 'system-ui', 'sans-serif'],
                'mono': ['JetBrains Mono', 'monospace'],
            },
            boxShadow: {
                'glow-cyan': '0 0 20px rgba(0, 212, 255, 0.3)',
                'glow-red': '0 0 20px rgba(255, 59, 59, 0.3)',
                'glow-purple': '0 0 20px rgba(124, 58, 237, 0.3)',
            },
            animation: {
                'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                'scan': 'scan 2s linear infinite',
            },
            keyframes: {
                scan: {
                    '0%': { transform: 'translateY(-100%)' },
                    '100%': { transform: 'translateY(100%)' },
                }
            },
            backdropBlur: {
                'xs': '2px',
            }
        },
    },
    plugins: [],
}
