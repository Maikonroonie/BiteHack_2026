import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react()],
    server: {
        port: 5173,
        host: '0.0.0.0', // Pozwala na podgląd mapy na telefonie/innym urządzeniu w sieci
        proxy: {
            '/api': {
                target: 'http://127.0.0.1:8000', // Adres Twojego backendu FastAPI
                changeOrigin: true,
                timeout: 600000,        // 10 minut (dla ciężkich analiz SAR)
                proxyTimeout: 600000,   // 10 minut na ustanowienie połączenia
            },
        },
    },
})