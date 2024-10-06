import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from sklearn.impute import SimpleImputer
import joblib
import requests
from datetime import datetime, timedelta
import logging
import time
import sys
from plant_database import plant_database

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Function to fetch climate data from NASA POWER API with retry mechanism
def get_nasa_power_data(lat, lon, max_retries=3, delay=5):
    base_url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    
    end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    start_date = end_date - timedelta(days=364)
    
    parameters = {
        "parameters": "T2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN,RH2M,WS2M,GWETPROF",
        "community": "AG",
        "longitude": lon,
        "latitude": lat,
        "start": start_date.strftime("%Y%m%d"),
        "end": end_date.strftime("%Y%m%d"),
        "format": "JSON"
    }
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Requesting NASA POWER data for lat: {lat}, lon: {lon} (Attempt {attempt + 1})")
            logger.info(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            response = requests.get(base_url, params=parameters)
            response.raise_for_status()
            data = response.json()
            
            if 'properties' not in data or 'parameter' not in data['properties']:
                logger.error("Unexpected API response structure")
                logger.debug(f"API response: {data}")
                return None
            
            df = pd.DataFrame(data['properties']['parameter'])
            
            averages = {
                'avg_temperature': df['T2M'].mean(),
                'avg_precipitation': df['PRECTOTCORR'].mean(),
                'avg_solar_radiation': df['ALLSKY_SFC_SW_DWN'].mean(),
                'avg_humidity': df['RH2M'].mean(),
                'avg_wind_speed': df['WS2M'].mean(),
                'avg_soil_moisture': df['GWETPROF'].mean()  # This is the root zone soil moisture
            }
            
            return averages
        
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error occurred: {e}")
            logger.debug(f"Response content: {e.response.content}")
            logger.debug(f"Request URL: {e.response.url}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching NASA POWER data: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        
        if attempt < max_retries - 1:
            logger.info(f"Retrying in {delay} seconds...")
            time.sleep(delay)
    
    logger.error(f"Failed to fetch NASA POWER data after {max_retries} attempts")
    return None

# Function to get soil data (placeholder)
def get_soil_data(lat, lon):
    # Placeholder data - replace with actual API call or data source
    return {
        'clay_content': 20,
        'sand_content': 30,
        'silt_content': 50,
        'soil_ph': 6.5,
        'soil_organic_carbon': 3,
        'soil_type': 'loam'
    }

# Function to combine climate and soil data
def get_land_data(lat, lon):
    climate_data = get_nasa_power_data(lat, lon)
    if climate_data is None:
        logger.error("Failed to get climate data")
        return None
    
    soil_data = get_soil_data(lat, lon)
    return {**climate_data, **soil_data}

# Function to load historical data from CSV
def load_historical_data(file_path):
    try:
        df = pd.read_csv(file_path)
        historical_data = df.to_dict('records')
        logger.info(f"Loaded {len(historical_data)} historical records from {file_path}")
        return historical_data
    except Exception as e:
        logger.error(f"Error loading historical data from {file_path}: {e}")
        return []

# Updated function to prepare data for the model
def prepare_data(historical_data, plant_database):
    X = []
    y = []
    for data in historical_data:
        X.append([
            data['avg_temperature'],
            data['avg_precipitation'],
            data['avg_solar_radiation'],
            data['avg_humidity'],
            data['avg_wind_speed'],
            data['avg_soil_moisture'],
            data['clay_content'],
            data['sand_content'],
            data['silt_content'],
            data['soil_ph'],
            data['soil_organic_carbon']
        ])
        y.append(data['successful_plant'])
    
    # Add data from plant_database
    for plant in plant_database:
        X.append([
            np.mean(plant['optimal_temperature']),
            np.mean(plant['optimal_precipitation']),
            np.mean(plant['optimal_solar_radiation']),
            np.mean(plant['optimal_humidity']),
            np.mean(plant['optimal_wind_speed']),
            np.mean(plant['optimal_soil_moisture']),
            np.mean(plant['optimal_clay_content']),
            np.mean(plant['optimal_sand_content']),
            np.mean(plant['optimal_silt_content']),
            np.mean(plant['optimal_soil_ph']),
            np.mean(plant['optimal_soil_organic_carbon'])
        ])
        y.append(plant['plant_name'])
    
    return np.array(X), np.array(y)

# Function to train the model
def train_model(X, y):
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    imputer = SimpleImputer(strategy='mean')
    X_train_imputed = imputer.fit_transform(X_train)
    X_test_imputed = imputer.transform(X_test)
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_imputed)
    X_test_scaled = scaler.transform(X_test_imputed)
    
    model = RandomForestClassifier(n_estimators=200, min_samples_split=5, min_samples_leaf=2, max_features='sqrt', random_state=42)
    model.fit(X_train_scaled, y_train)
    
    y_pred = model.predict(X_test_scaled)
    accuracy = accuracy_score(y_test, y_pred)
    logger.info(f"Model Accuracy: {accuracy:.2f}")
    logger.info("\nClassification Report:")
    logger.info(classification_report(y_test, y_pred))
    
    return model, imputer, scaler

# Function to save the trained model
def save_model(model, imputer, scaler, filename='plant_recommendation_model'):
    joblib.dump((model, imputer, scaler), f"{filename}.joblib")
    logger.info(f"Model saved as {filename}.joblib")

# Function to load a saved model
def load_model(filename='plant_recommendation_model'):
    model, imputer, scaler = joblib.load(f"{filename}.joblib")
    return model, imputer, scaler

# Function to recommend plants based on land data
def recommend_plants(lat, lon, model, imputer, scaler, plant_database):
    land_data = get_land_data(lat, lon)
    if land_data is None:
        logger.error("Unable to get land data for recommendations")
        return []
    
    input_data = np.array([[
        land_data['avg_temperature'],
        land_data['avg_precipitation'],
        land_data['avg_solar_radiation'],
        land_data['avg_humidity'],
        land_data['avg_wind_speed'],
        land_data['avg_soil_moisture'],
        land_data['clay_content'],
        land_data['sand_content'],
        land_data['silt_content'],
        land_data['soil_ph'],
        land_data['soil_organic_carbon']
    ]])
    
    input_imputed = imputer.transform(input_data)
    input_scaled = scaler.transform(input_imputed)
    
    probabilities = model.predict_proba(input_scaled)[0]
    plant_scores = list(zip(model.classes_, probabilities))
    
    recommendations = sorted(plant_scores, key=lambda x: x[1], reverse=True)[:5]
    
    plant_recommendations = []
    for plant, score in recommendations:
        plant_data = next((item for item in plant_database if item['plant_name'] == plant), None)
        if plant_data:
            plant_recommendations.append({'plant': plant, 'score': score, 'data': plant_data})
    
    return plant_recommendations

# Main function
def main():
    latitude = 40.7128
    longitude = -74.0060
    
    force_retrain = '--retrain' in sys.argv
    
    try:
        if force_retrain:
            raise Exception("Forced retraining")
        model, imputer, scaler = load_model()
        logger.info("Model loaded successfully")
    except Exception as e:
        logger.info(f"Training new model... (Reason: {e})")
        
        # Load historical data from CSV
        historical_data = load_historical_data('C:/Users/user/Desktop/mmm/plant_historical_data.csv')
        
        if not historical_data:
            logger.error("No historical data available. Cannot train model.")
            return
        
        X, y = prepare_data(historical_data, plant_database)
        model, imputer, scaler = train_model(X, y)
        save_model(model, imputer, scaler)
    
    recommendations = recommend_plants(latitude, longitude, model, imputer, scaler, plant_database)
    
    if recommendations:
        logger.info("Plant Recommendations:")
        for rec in recommendations:
            logger.info(f"Recommended plant: {rec['plant']} with score {rec['score']:.2f}")
            logger.info(f"Plant data: {rec['data']}")
    else:
        logger.info("No recommendations available.")

if __name__ == "__main__":
    main()