# Simulator Data Validation Report

## Overview

This report validates that the simulator uses correct data and assumptions based on the CSV data validation findings.

---

## ✅ Check 1: Pump Flow Column Usage

**Status**: ✓ **CORRECT**

The simulator correctly uses the `'Sum of pumped flow to WWTP F2'` column for target flowrates (see `main.py` lines 55-56).

```python
target_flowrates_m3h = [float(x) for x in simulation_data['Sum of pumped flow to WWTP F2'].tolist()]
target_flowrates = [flow / 4.0 for flow in target_flowrates_m3h]  # Convert m³/h to m³/15min
```

**Validation Report Finding**: The validation report recommends using "Sum of pumped flow F2" rather than summing individual flows, as it appears to be the authoritative source. The simulator follows this recommendation.

**Note**: The simulator calculates actual outflow by summing individual pump flows during simulation. This is correct for simulation purposes, as it models what the pumps would actually produce based on their characteristics and water level.

---

## ✅ Check 2: Level-Volume Relationship

**Status**: ✓ **ACCEPTABLE**

The simulator uses a 4-case formula in `tunnel.py` to convert between water level and volume.

### Accuracy Comparison:

| Model | RMSE | Mean Abs Diff | Median Abs Diff | Max Diff |
|-------|------|---------------|----------------|----------|
| **Simulator 4-case formula** | **40.20 m³** | 22.24 m³ | 9.86 m³ | 283.30 m³ |
| Validation polynomial model | 41.90 m³ | - | - | - |

**Findings**:
- The simulator's 4-case formula is **reasonably accurate** (RMSE: 40.20 m³)
- It performs **slightly better** than the polynomial model from the validation report (41.90 m³)
- 49.9% of rows have differences > 10 m³
- 11.5% of rows have differences > 50 m³
- 4.4% of rows have differences > 100 m³

**Worst Case**:
- Level: 0.6454 m
- Actual volume: 783.82 m³
- Simulator volume: 500.52 m³
- Difference: 283.30 m³ (36.14% relative error)

**Conclusion**: The 4-case formula is acceptable for simulation purposes. The polynomial model from the validation report is not significantly better, so no changes are needed.

---

## ✅ Check 3: Units and Conversions

**Status**: ✓ **CORRECT**

### Inflow (F1):
- **CSV unit**: m³/15min ✓
- **Simulator expects**: m³/15min ✓
- **Status**: No conversion needed - correct

### Target Flowrate (F2):
- **CSV unit**: m³/h
- **Simulator expects**: m³/15min
- **Conversion**: Divides by 4 (m³/h → m³/15min) ✓
- **Status**: Correct conversion

**Example**:
- CSV value: 4515.64 m³/h
- Simulator converts to: 1128.91 m³/15min (4515.64 / 4)
- ✓ Correct

---

## ✅ Check 4: Volume Balance Equation

**Status**: ✓ **CORRECT**

The simulator uses the correct volume balance equation:

```python
# From simulator.py line 389
volume_change = inflow - outflow
self.current_volume += volume_change
```

**Validation Report Finding**: The volume balance is mathematically perfect in the CSV data (Volume Change = Inflow - Pumped Flow). The simulator correctly implements this equation.

---

## ✅ Check 5: Level Boundaries

**Status**: ✓ **WITHIN RANGE**

- **Data level range**: -0.02 to 5.26 m
- **Simulator maximum level (RAJA_4)**: 14.10 m
- **Status**: All data levels are within the simulator's valid range

---

## Summary

| Check | Status | Notes |
|-------|--------|-------|
| Pump Flow Column | ✓ | Uses correct column ('Sum of pumped flow to WWTP F2') |
| Level-Volume Formula | ✓ | 4-case formula is reasonably accurate (RMSE: 40.20 m³) |
| Units & Conversions | ✓ | Correctly handles m³/15min for inflow and converts F2 from m³/h |
| Volume Balance | ✓ | Uses correct equation (Inflow - Outflow) |
| Level Boundaries | ✓ | All data within valid range |

---

## Recommendations

1. ✅ **Continue using current approach**: The simulator correctly uses the recommended data columns and formulas.

2. ✅ **4-case formula is acceptable**: The simulator's level-volume relationship is accurate enough for simulation purposes. No need to switch to the polynomial model.

3. ✅ **No changes needed**: All data usage and assumptions are correct based on the validation findings.

---

## Notes

- The simulator calculates outflow by summing individual pump flows during simulation. This is correct for simulation purposes, as it models actual pump behavior based on water level and pump characteristics.

- While the validation report found discrepancies between summing individual flows and the "Sum of pumped flow F2" column in the historical data, this is expected and acceptable. The simulator models what the pumps *should* produce, not necessarily what was recorded historically (which may have measurement errors).

- The volume balance equation is implemented correctly and matches the perfect balance confirmed in the validation report.

