# Run POL on a single provider
python run_analysis.py --provider 12345

# Run NYC sweep
python run_analysis.py --sweep --min-risk 70 --output high_risk.csv

# Generate attorney packages
python run_analysis.py --export --case-id 5
