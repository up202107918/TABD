# Data Directory

This directory is used by the ETL pipeline to store downloaded and processed data.

## Subdirectories

- `downloads/` - Raw downloaded files from CNE and DGT
- `extracted/` - Extracted contents from ZIP archives
- `processed/` - Cleaned and processed data files
- `logs/` - ETL execution logs

## Note

These directories are created automatically by the ETL pipeline when it runs.
The `.gitignore` file should exclude these directories from version control due to large file sizes.
