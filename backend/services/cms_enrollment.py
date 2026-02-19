import requests
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
import io
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_latest_enrollment_data():
    """Fetch the latest Medicaid/CHIP Performance Indicator CSV from CMS (contains total enrollment by state/month)"""
    base_url = "https://download.medicaid.gov/data/"
    month_names = [
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december"
    ]

    # Start from current month and go back up to 12 months
    current_date = datetime.now()
    for offset in range(0, 12):
        trial_date = current_date - pd.DateOffset(months=offset)
        month_str = month_names[trial_date.month - 1]
        year_str = trial_date.year
        filename = f"pi-dataset-{month_str}-{year_str}release.csv"
        url = base_url + filename

        logger.info(f"Attempting to download: {url}")
        response = requests.get(url)
        if response.status_code == 200:
            logger.info(f"Successfully downloaded latest data: {filename}")
            df = pd.read_csv(io.StringIO(response.text))
            return df

    raise ValueError("Could not find a recent PI dataset in the last 12 months. Check CMS download page manually.")

def update_dashboard_stats(engine):
    """Update the enrollment_stats table with the latest national + NY enrollment numbers"""
    # Fetch and parse the latest CMS data
    df = fetch_latest_enrollment_data()

    logger.info(f"Dataset columns: {df.columns.tolist()}")

    # Standardize report date column (common names: 'report_date', 'Report Date', 'month', etc.)
    date_col = next((col for col in df.columns if 'date' in col.lower() or 'month' in col.lower() or 'period' in col.lower()), None)
    if date_col is None:
        raise ValueError("Could not find date/month column in dataset")
    
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    latest_date = df[date_col].max()
    if pd.isna(latest_date):
        raise ValueError("Invalid dates in dataset")
    
    latest_df = df[df[date_col] == latest_date].copy()
    logger.info(f"Using data for latest month: {latest_date.strftime('%Y-%m')}")

    # Find enrollment column (flexible matching)
    enrollment_col = next((
        col for col in latest_df.columns 
        if 'total_medicaid' in col.lower() and 'enroll' in col.lower()
    ), None)
    if enrollment_col is None:
        raise ValueError("Could not find total Medicaid enrollment column")

    # Find state column
    state_col = next((col for col in latest_df.columns if 'state' in col.lower()), None)
    if state_col is None:
        raise ValueError("Could not find state column")

    # National total (look for United States / Nationwide / Total row)
    national_row = latest_df[
        latest_df[state_col].str.contains('United States|Nationwide|Total', case=False, na=False)
    ]
    if not national_row.empty:
        total_enrollment = int(national_row[enrollment_col].iloc[0])
    else:
        # Fallback: sum across states
        total_enrollment = int(latest_df[enrollment_col].sum())
        logger.warning("No national total row found – using sum of states")

    # New York
    ny_row = latest_df[latest_df[state_col].str.contains('New York', case=False, na=False)]
    if ny_row.empty:
        raise ValueError("New York data not found in latest dataset")
    ny_enrollment = int(ny_row[enrollment_col].iloc[0])

    month_str = latest_date.strftime('%Y-%m')

    logger.info(f"Latest stats → Month: {month_str}, National: {total_enrollment:,}, NY: {ny_enrollment:,}")

    with engine.begin() as conn:  # begin() for auto-commit
        # Create table with PRIMARY KEY on month for upsert
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS enrollment_stats (
                month VARCHAR(7) PRIMARY KEY,
                total_enrollment BIGINT NOT NULL,
                ny_enrollment BIGINT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # Upsert the latest values
        conn.execute(text("""
            INSERT INTO enrollment_stats (month, total_enrollment, ny_enrollment)
            VALUES (:month, :total, :ny)
            ON CONFLICT (month) DO UPDATE SET
                total_enrollment = EXCLUDED.total_enrollment,
                ny_enrollment = EXCLUDED.ny_enrollment,
                updated_at = CURRENT_TIMESTAMP
        """), {
            "month": month_str,
            "total": total_enrollment,
            "ny": ny_enrollment
        })

    logger.info("Dashboard enrollment stats updated successfully!")

# Example usage (uncomment/adapt for your environment)
# if __name__ == "__main__":
#     engine = create_engine("postgresql://user:password@localhost:5432/medifraudy")
#     update_dashboard_stats(engine)