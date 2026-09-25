#!/bin/bash

DB_NAME="gis"
DB_USER="postgres"
DB_HOST="localhost"
DB_PORT=5433
SRID=4326
SHAPE_DIR="/Users/lorenajakic/Downloads/croatia-latest-free"

# Koristi punu putanju do psql (Homebrew)
PSQL="/opt/homebrew/bin/psql"
SHP2PGSQL="/opt/homebrew/bin/shp2pgsql"

# Provjeri postoji li baza
if ! $PSQL -h $DB_HOST -p $DB_PORT -U $DB_USER -lqt 2>/dev/null | cut -d \| -f 1 | grep -qw $DB_NAME; then
    echo "Creating database $DB_NAME..."
    $PSQL -h $DB_HOST -p $DB_PORT -U $DB_USER -c "CREATE DATABASE $DB_NAME;"
fi

# Provjeri postoji li PostGIS ekstenzija
echo "Checking PostGIS extension..."
$PSQL -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS postgis;" 2>/dev/null

for SHP_FILE in $SHAPE_DIR/*.shp
do
    if [ ! -f "$SHP_FILE" ]; then
        echo "Warning: $SHP_FILE not found, skipping..."
        continue
    fi
    
    echo "Using shp2pgsql from: $SHP2PGSQL"
    BASE_NAME=$(basename "$SHP_FILE" .shp)
    TABLE_NAME="$BASE_NAME"
    
    echo "Importing $SHP_FILE into table $TABLE_NAME ..."
    
    # Generiraj SQL i pošalji u psql
    $SHP2PGSQL -I -s $SRID "$SHP_FILE" "$TABLE_NAME" | $PSQL -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME
    
    if [ $? -eq 0 ]; then
        echo "✓ Successfully imported $TABLE_NAME"
    else
        echo "✗ Failed to import $TABLE_NAME"
    fi
done 

echo "All shapefiles imported!"