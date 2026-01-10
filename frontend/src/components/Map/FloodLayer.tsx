/**
 * CrisisEye - FloodLayer Component
 * Warstwa GeoJSON z wizualizacją powodzi
 */

import { GeoJSON, Popup } from 'react-leaflet';
import type { FloodGeoJSON, FloodFeature } from '../../types';
import type { PathOptions } from 'leaflet';

interface FloodLayerProps {
    data: FloodGeoJSON;
}

export function FloodLayer({ data }: FloodLayerProps) {
    /**
     * Style dla polygonów powodzi
     * Kolor zależy od prawdopodobieństwa zalania
     */
    const getStyle = (feature: FloodFeature): PathOptions => {
        const probability = feature.properties.flood_probability || 0;

        // Gradient: niebieski -> czerwony w zależności od ryzyka
        const hue = (1 - probability) * 200; // 200 (niebieski) -> 0 (czerwony)
        const color = `hsl(${hue}, 80%, 50%)`;

        return {
            fillColor: color,
            fillOpacity: 0.5 + probability * 0.3,
            color: 'rgba(0, 212, 255, 0.8)',
            weight: 1,
        };
    };

    /**
     * Popup przy kliknięciu na obszar
     */
    const onEachFeature = (feature: FloodFeature, layer: any) => {
        const props = feature.properties;

        const popupContent = `
      <div class="text-sm">
        <div class="font-semibold text-cyber-cyan mb-2">Flood Risk Zone</div>
        <div class="space-y-1">
          <div>
            <span class="text-gray-400">Probability:</span>
            <span class="font-mono ml-2">${(props.flood_probability * 100).toFixed(0)}%</span>
          </div>
          ${props.area_km2 ? `
          <div>
            <span class="text-gray-400">Area:</span>
            <span class="font-mono ml-2">${props.area_km2.toFixed(2)} km²</span>
          </div>
          ` : ''}
        </div>
      </div>
    `;

        layer.bindPopup(popupContent);

        // Hover effect
        layer.on({
            mouseover: (e: any) => {
                const layer = e.target;
                layer.setStyle({
                    fillOpacity: 0.8,
                    weight: 2,
                });
            },
            mouseout: (e: any) => {
                const layer = e.target;
                layer.setStyle(getStyle(feature));
            },
        });
    };

    if (!data || !data.features || data.features.length === 0) {
        return null;
    }

    return (
        <GeoJSON
            key={JSON.stringify(data)} // Force re-render on data change
            data={data as any}
            style={(feature) => getStyle(feature as FloodFeature)}
            onEachFeature={onEachFeature}
        />
    );
}
