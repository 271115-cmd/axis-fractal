"""
landmarks.py — Central Axis landmark heights: the vertical rhythm.  [PHASE 9b/10 support]

WHY THIS EXISTS
    Height is the weakest data in this project: only ~3% of Beijing footprints carry a real
    height from Overture; the rest fall back to a 7 m zone median (see export3d.py). That
    flattens the Axis into pancakes and throws away its whole drama — the Axis is a SEQUENCE
    OF PEAKS: towers ~47 m north, the palace deliberately low-and-wide at 35 m, Qianmen
    spiking to 43.65 m, resolving at Yongdingmen's 26 m.

HONESTY / PROVENANCE
    Heights are published facts from official/primary sources (Palace Museum, Beijing
    municipal sites, Wikipedia) — each row carries its source URL. Positions are geocoded
    from OpenStreetMap (our licensed source). Nothing here is estimated or invented; where a
    figure is unverified it is marked and NOT used (see JINGSHAN_HILL_M).

    Reference note: 云上中轴 (Beijing Cultural Heritage Bureau × Tencent) is an excellent
    visual reference for proportion/colour/relation, but its 3D assets are proprietary — we
    read published facts and build our own geometry instead of extracting theirs.
"""
from __future__ import annotations

import geopandas as gpd
import numpy as np
from shapely.geometry import Point

# name -> (lat, lon [OSM geocode], height_m, source)
LANDMARKS = {
    "bell_tower": dict(
        zh="钟楼", en="Bell Tower", lat=39.94105, lon=116.38964, height_m=47.9,
        source="https://zh.wikipedia.org/zh-cn/北京中轴线"),
    "drum_tower": dict(
        zh="鼓楼", en="Drum Tower", lat=39.93932, lon=116.38975, height_m=46.7,
        source="https://zh.wikipedia.org/zh-cn/北京中轴线"),
    "wanchun_ting": dict(
        zh="万春亭", en="Wanchun Pavilion (Jingshan)", lat=39.92352, lon=116.39049, height_m=15.38,
        source="https://gygl.beijing.gov.cn/mlgy/mlgy_gyjg01/201912/t20191211_1048536.html",
        note="Pavilion only. It stands on the artificial Jingshan hill, which is TERRAIN we do "
             "not model — see JINGSHAN_HILL_M (unverified, unused)."),
    "taihedian": dict(
        zh="太和殿", en="Hall of Supreme Harmony", lat=39.91594, lon=116.39081, height_m=35.05,
        source="https://www.dpm.org.cn/explore/building/236465.html",
        note="Includes the 台基 (terrace)."),
    "tiananmen": dict(
        zh="天安门", en="Tiananmen", lat=39.90736, lon=116.39126, height_m=34.7,
        source="https://news.qq.com/rain/a/20240910A000UN00"),
    "zhengyangmen": dict(
        zh="正阳门", en="Zhengyangmen (Qianmen)", lat=39.89921, lon=116.39162, height_m=43.65,
        source="https://www.beijing.gov.cn/shipin/bjfq/18938.html",
        note="Tallest of all the old city gate towers."),
    "yongdingmen": dict(
        zh="永定门", en="Yongdingmen", lat=39.87105, lon=116.39311, height_m=26.0,
        source="https://www.bjdch.gov.cn/mldc/bglj/whgj/202008/t20200827_2975733.html"),
}

# The Jingshan mound is terrain, not a footprint. Commonly cited around 45-48 m, but we have
# NOT verified it against a primary source, so it is deliberately unused. Verify before use.
JINGSHAN_HILL_M = None   # TODO: verify from a primary source before modelling the hill.


def apply_landmark_heights(gdf: gpd.GeoDataFrame, crs: str, radius_m: float = 70.0,
                           height_col: str = "height") -> gpd.GeoDataFrame:
    """Stamp published landmark heights onto the footprints that sit under them.

    Any footprint whose centroid is within `radius_m` of a landmark takes that landmark's
    published height, and is tagged height_src='landmark_published' so nothing is silently
    overwritten. Everything else keeps whatever export3d gave it.
    """
    gdf = gdf.copy()
    if height_col not in gdf.columns:
        gdf[height_col] = np.nan
    if "height_src" not in gdf.columns:
        gdf["height_src"] = "overture_or_default"
    gdf["landmark"] = ""

    cent = gdf.geometry.centroid
    for key, L in LANDMARKS.items():
        p = gpd.GeoSeries([Point(L["lon"], L["lat"])], crs="EPSG:4326").to_crs(crs).iloc[0]
        hit = cent.distance(p) <= radius_m
        n = int(hit.sum())
        if n:
            gdf.loc[hit, height_col] = L["height_m"]
            gdf.loc[hit, "height_src"] = "landmark_published"
            gdf.loc[hit, "landmark"] = key
        print(f"  {L['zh']:<4} {L['en']:<28} {L['height_m']:>5.2f} m -> {n:>3} footprint(s)")
    return gdf


def summary() -> str:
    lines = ["Central Axis landmark heights (published, cited):"]
    for k, L in LANDMARKS.items():
        lines.append(f"  {L['zh']} {L['en']}: {L['height_m']} m  [{L['source']}]")
    return "\n".join(lines)


if __name__ == "__main__":
    print(summary())
