#This module provides functions to export market data, positions, and risk metrics to various formats.
import pandas as pd
import json
import logging

logger = logging.getLogger(__name__)

# --- CSV Export Functions ---
def export_to_csv(data, filename="market_data.csv"):
    # Export data to CSV format.
    try:
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False)
        logger.info(f"Data exported to {filename}")
    except Exception as e:
        logger.error(f"Error exporting to CSV: {e}")

# --- JSON Export Functions ---
def export_to_json(data, filename="market_data.json"):
    # Export data to JSON format.
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Data exported to {filename}")
    except Exception as e:
        logger.error(f"Error exporting to JSON: {e}")

# --- Risk Metrics Export ---
def export_risk_report(positions, risk_metrics, filename="risk_report.csv"):
    # Export comprehensive risk report including positions and metrics.
    try:
        # Combine positions and risk metrics
        report_data = {
            'positions': positions,
            'risk_metrics': risk_metrics,
            'timestamp': pd.Timestamp.now().isoformat()
        }
        # Export to both CSV and JSON for flexibility
        export_to_csv(report_data, filename)
        export_to_json(report_data, filename.replace('.csv', '.json'))
        logger.info(f"Risk report exported to {filename}")
    except Exception as e:
        logger.error(f"Error exporting risk report: {e}")