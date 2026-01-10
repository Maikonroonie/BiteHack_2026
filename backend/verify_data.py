import asyncio
import numpy as np
from datetime import date
from services.sar_processor import SARProcessor
from services.gee_service import gee_service
from config import settings

async def test_integration():
    print("🚀 Rozpoczynam weryfikację źródeł danych...")
    
    # 1. Test Microsoft Planetary Computer (SAR)
    sar = SARProcessor()
    bbox = [16.90, 51.05, 17.10, 51.15]  # Przykład: Wrocław
    test_date = date(2024, 9, 15) # Przykładowa data powodzi
    
    try:
        print("\n📡 Testuję pobieranie SAR z Microsoft STAC...")
        sar_result = await sar.process_sar(bbox, test_date)
        print(f"✅ Sukces! Pobrano macierz SAR o kształcie: {sar_result['after'].shape}")
        print(f"   Średnia wartość dB: {np.mean(sar_result['after']):.2f}")
    except Exception as e:
        print(f"❌ Błąd SAR: {e}")

    # 2. Test Google Earth Engine (DEM & Rain)
    try:
        print("\n🌍 Testuję GEE (DEM i Opady)...")
        # Musisz mieć ustawione GEE_PROJECT_ID w .env lub systemie
        gee_data = await gee_service.get_terrain_and_rain(bbox)
        
        if gee_data:
            print(f"✅ Sukces! Dane z GEE:")
            print(f"   Wysokość terenu (avg): {gee_data.get('avg_elevation'):.2f} m")
            print(f"   Aktualny opad (avg): {gee_data.get('current_rainfall'):.2f} mm/h")
        else:
            print("⚠️ GEE zwróciło pusty wynik (sprawdź uprawnienia).")
    except Exception as e:
        print(f"❌ Błąd GEE: {e}")

if __name__ == "__main__":
    asyncio.run(test_integration())