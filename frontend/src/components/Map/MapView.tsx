/**
 * CrisisEye - MapView Component
 * Główna mapa z react-leaflet i OpenStreetMap
 */

import { useRef, useEffect, useState } from "react";
import {
  MapContainer,
  TileLayer,
  useMap,
  useMapEvents,
  FeatureGroup,
} from "react-leaflet";
import { EditControl } from "react-leaflet-draw";
import { motion } from "framer-motion";
import type { BoundingBox, FloodGeoJSON } from "../../types";
import { FloodLayer } from "./FloodLayer";

// Need to import Leaflet draw CSS
import "leaflet-draw/dist/leaflet.draw.css";

interface MapViewProps {
  floodData: FloodGeoJSON | null;
  onBoundsSelect: (bbox: BoundingBox) => void;
  center?: [number, number];
  zoom?: number;
}

// Component to handle rectangle drawing
function DrawControl({
  onBoundsSelect,
}: {
  onBoundsSelect: (bbox: BoundingBox) => void;
}) {
  useMapEvents({
    // @ts-ignore - Leaflet Draw event nie jest w standardowych typach React Leaflet
    "draw:created": (e: any) => {
      const layer = e.layer;
      const bounds = layer.getBounds();

      onBoundsSelect({
        min_lon: bounds.getWest(),
        min_lat: bounds.getSouth(),
        max_lon: bounds.getEast(),
        max_lat: bounds.getNorth(),
      });
    },
  });

  return (
    <FeatureGroup>
      <EditControl
        position="topright"
        onCreated={() => {}}
        draw={{
          rectangle: true,
          polygon: false,
          circle: false,
          circlemarker: false,
          marker: false,
          polyline: false,
        }}
      />
    </FeatureGroup>
  );
}

// Map position tracker
function MapPosition({
  onMoveEnd,
}: {
  onMoveEnd: (center: [number, number], zoom: number) => void;
}) {
  const map = useMapEvents({
    moveend: () => {
      const center = map.getCenter();
      onMoveEnd([center.lat, center.lng], map.getZoom());
    },
  });
  return null;
}

export function MapView({
  floodData,
  onBoundsSelect,
  center = [51.1, 17.03], // Wrocław default
  zoom = 12,
}: MapViewProps) {
  const [mapCenter, setMapCenter] = useState<[number, number]>(center);
  const [mapZoom, setMapZoom] = useState(zoom);

  return (
    <motion.div
      className="h-full w-full rounded-xl overflow-hidden border border-orbital-border"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5 }}
    >
      <MapContainer
        center={center}
        zoom={zoom}
        className="h-full w-full"
        zoomControl={true}
      >
        {/* Dark OSM tiles */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Flood overlay */}
        {floodData && <FloodLayer data={floodData} />}

        {/* Drawing controls */}
        <FeatureGroup>
          <DrawControl onBoundsSelect={onBoundsSelect} />
        </FeatureGroup>

        {/* Position tracker */}
        <MapPosition
          onMoveEnd={(c, z) => {
            setMapCenter(c);
            setMapZoom(z);
          }}
        />
      </MapContainer>

      {/* Map overlay info */}
      <div className="absolute bottom-4 right-4 glass px-3 py-2 rounded-lg z-[1000]">
        <div className="text-xs font-mono text-gray-400">
          {mapCenter[0].toFixed(4)}, {mapCenter[1].toFixed(4)} | z{mapZoom}
        </div>
      </div>
    </motion.div>
  );
}
