# Hand-digitizing flagged hutong tiles (QGIS)

Some tiles fell below the coverage flag and MAY be missing building/alley data.
Check each against imagery; digitize only where OSM is genuinely incomplete.

1. Open QGIS. Add a satellite basemap (Browser > XYZ Tiles > add Esri World Imagery:
   `https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}`).
2. Drag in `hutong_flagged_tiles.geojson` (the tiles to inspect) and
   `hutong_digitize_template.geojson` (the empty layer to trace into).
3. Toggle editing on the template layer; trace missing building footprints as polygons.
   Fill `tile_id` (matching the flagged tile), `feature`='building', add any `note`.
4. Save. Phase 2 can rasterize these hand-traced polygons alongside the OSM data.

NOTE: A tile can be legitimately empty (park, lake, plaza). Do NOT invent buildings —
only trace what is visibly there in the imagery. Honesty over completeness.
