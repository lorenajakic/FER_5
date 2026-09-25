#!/usr/bin/env python3
import os
import subprocess

# Putanja do foldera s shapefileovima
shp_folder = "/Users/lorenajakic/Downloads/HRV_adm"

# Folder gdje ce se spremiti SQL fajlovi
output_folder = "output_hrv2"
os.makedirs(output_folder, exist_ok=True)

# EPSG kod (provjeri .prj fajlove, najcesce 3765 za Hrvatsku)
epsg = 3765

# PostgreSQL schema
schema = "public"

# Iteriraj kroz sve .shp fajlove
for file in os.listdir(shp_folder):
    if file.endswith(".shp"):
        shp_path = os.path.join(shp_folder, file)
        table_name = os.path.splitext(file)[0]  # ime shapefile-a kao ime tablice
        sql_file = os.path.join(output_folder, f"{table_name}.sql")

        print(f"Generiram SQL za {file} -> {sql_file}")
        
        # Pokreni shp2pgsql
        cmd = [
            "shp2pgsql",
            "-I",       # kreira GIST indeks
            "-s", str(epsg),
            shp_path,
            f"{schema}.{table_name}"
        ]
        
        with open(sql_file, "w") as f:
            subprocess.run(cmd, stdout=f)

print("Gotovo! Svi SQL fajlovi su spremljeni u:", output_folder)