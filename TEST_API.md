# API Testing with cURL

## Base URL
Assuming the API is running on `http://localhost:8000`

## 1. Health Check
```bash
curl -X GET "http://localhost:8000/health"
```

## 2. Get Latest Simulation
```bash
curl -X GET "http://localhost:8000/"
```

## 3. Get All Simulations
```bash
curl -X GET "http://localhost:8000/all"
```

## 4. Create Simulation (Auto-fetch data)
This will automatically fetch rain forecast, electricity prices, and average daily inflow from CSV:
```bash
curl -X POST "http://localhost:8000/simulate" \
  -H "Content-Type: application/json" \
  -d '{}'
```

Or simply:
```bash
curl -X POST "http://localhost:8000/simulate"
```

## 5. Create Simulation with Manual Data
```bash
curl -X POST "http://localhost:8000/simulate" \
  -H "Content-Type: application/json" \
  -d '{
    "rain_forecast": [0.0, 0.0, 0.5, 1.0, 0.5, 0.0],
    "electricity_prices": [0.1, 0.12, 0.15, 0.13, 0.11, 0.1],
    "inflow_estimates": [100.0, 110.0, 120.0, 115.0, 105.0, 100.0],
    "starting_water_level": 5.0,
    "target_flowrates": [110.0, 121.0, 132.0, 126.5, 115.5, 110.0]
  }'
```

Note: The arrays above are shortened examples. In reality, you need 96 values (24 hours * 4 periods) for each array.

## 6. Create Simulation with Partial Data (Auto-fetch missing)
```bash
curl -X POST "http://localhost:8000/simulate" \
  -H "Content-Type: application/json" \
  -d '{
    "starting_water_level": 6.0
  }'
```

This will use the provided starting water level but auto-fetch rain forecast, electricity prices, and inflow estimates.

## Pretty Print JSON Response
Add `| jq` to any command for formatted output:
```bash
curl -X GET "http://localhost:8000/" | jq
```

Or use Python for formatting:
```bash
curl -X GET "http://localhost:8000/" | python -m json.tool
```

## Example: Full Workflow
```bash
# 1. Check health
curl -X GET "http://localhost:8000/health"

# 2. Create a simulation
curl -X POST "http://localhost:8000/simulate"

# 3. Get the latest simulation
curl -X GET "http://localhost:8000/" | jq

# 4. Get all simulations
curl -X GET "http://localhost:8000/all" | jq
```

