import pandas as pd

#Define the logical data for different plants
data = {
    'plant_name': ['Tomato', 'Lettuce', 'Carrot', 'Cucumber', 'Pepper'],
    'avg_temperature': [24.0, 20.0, 18.0, 26.0, 22.0],  # °C
    'avg_precipitation': [120.0, 200.0, 150.0, 100.0, 80.0],  # mm
    'avg_solar_radiation': [250.0, 220.0, 200.0, 260.0, 240.0],  # W/m²
    'avg_humidity': [60.0, 70.0, 50.0, 65.0, 55.0],  # %
    'avg_wind_speed': [2.5, 1.5, 1.0, 3.0, 2.0],  # m/s
    'avg_soil_moisture': [0.30, 0.35, 0.25, 0.28, 0.30],  # fraction
    'clay_content': [20.0, 15.0, 10.0, 12.0, 15.0],  # %
    'sand_content': [30.0, 35.0, 40.0, 38.0, 25.0],  # %
    'silt_content': [50.0, 50.0, 50.0, 50.0, 60.0],  # %
    'soil_ph': [6.5, 6.0, 6.8, 6.3, 6.7],  # pH
    'soil_organic_carbon': [3.0, 4.0, 2.0, 3.5, 3.2],  # %
    'successful_plant': [1, 1, 1, 1, 0]  # 1 = success, 0 = failure
}

#Create DataFrame
historical_data = pd.DataFrame(data)

#Save to CSV
historical_data.to_csv('plant_historical_data.csv', index=False)
print("Logical plant-specific historical data saved to 'plant_historical_data.csv'")
