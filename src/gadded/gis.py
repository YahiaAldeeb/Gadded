"""Preliminary GIS site screening using Shapely over a local GeoJSON layer set.

Stands in for PostGIS in the full-product spec: same checks (industrial-zone membership,
protected-area intersection, nearest substation/road distance, coverage), same output
shape (``GisFinding``), no database.

Distances are computed in an equirectangular local projection centered on the site
(a linear-scale approximation valid at km-scale near a fixed latitude), not raw
lat/lon degrees — the code-standards rule "reproject before planar distance math"
is satisfied without adding a full projection-library dependency. This is a demo-scale
approximation and is labeled as such; it is not suitable for country-scale mapping.

A category with no features in the loaded layer set returns an ``unknown`` coverage
finding rather than silently implying the feature does not exist.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon, shape
from shapely.ops import transform

from gadded.contracts import GisFinding

GIS_METHOD_VERSION = "shapely-local-equirectangular-0.1.0"
_EARTH_RADIUS_M = 6_371_000.0


@dataclass
class ZoneLayer:
    manifest: dict
    features: list[tuple[dict, object]]  # (properties, shapely geometry in lon/lat)

    def by_category(self, category: str) -> list[tuple[dict, object]]:
        return [(p, g) for p, g in self.features if p["category"] == category]

    def has_category(self, category: str) -> bool:
        return any(p["category"] == category for p, _ in self.features)


def load_zones(path: str | Path) -> ZoneLayer:
    """Load the GeoJSON layer set and its manifest."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    features = [(f["properties"], shape(f["geometry"])) for f in data["features"]]
    return ZoneLayer(manifest=data.get("manifest", {}), features=features)


def _local_projector(origin_lat_deg: float):
    """Return a lon/lat -> local meter (x, y) transform centered on origin_lat_deg.

    Equirectangular approximation: dx = dlon * R * cos(lat0), dy = dlat * R.
    Accurate to well under 1% for distances up to a few tens of km near the origin —
    adequate for rooftop-solar site screening, not for national-scale GIS.
    """
    lat0 = math.radians(origin_lat_deg)
    cos_lat0 = math.cos(lat0)

    def _fn(lon, lat):
        x = math.radians(lon) * _EARTH_RADIUS_M * cos_lat0
        y = math.radians(lat) * _EARTH_RADIUS_M
        return x, y

    return _fn


def _to_local(geom, projector):
    return transform(lambda lon, lat, z=None: projector(lon, lat), geom)


def screen_site(latitude: float, longitude: float, zones: ZoneLayer) -> list[GisFinding]:
    """Run point-in-polygon and nearest-distance checks for a site."""
    checked_at = datetime.now(timezone.utc).isoformat()
    site = Point(longitude, latitude)
    projector = _local_projector(latitude)
    site_m = _to_local(site, projector)

    findings: list[GisFinding] = []

    # --- industrial zone membership --------------------------------------------------
    if zones.has_category("industrial_zone"):
        matches = [p for p, g in zones.by_category("industrial_zone") if g.contains(site)]
        if matches:
            for p in matches:
                findings.append(
                    GisFinding(
                        code="industrial_zone.inside",
                        category="industrial_zone",
                        severity="info",
                        title=f"Site is inside {p['name']}",
                        value=p["name"],
                        layerId=p["id"],
                        sourceName=p["source_name"],
                        sourceDate=p.get("source_date"),
                        checkedAt=checked_at,
                        methodology="Shapely point-in-polygon (EPSG:4326 coordinates).",
                        limitations=[zones.manifest.get("provenance", "")],
                    )
                )
        else:
            findings.append(
                GisFinding(
                    code="industrial_zone.not_found",
                    category="industrial_zone",
                    severity="warning",
                    title="Site not found inside any mapped industrial zone",
                    value=False,
                    layerId="industrial_zone",
                    sourceName="gadded-gis-layers",
                    checkedAt=checked_at,
                    methodology="Shapely point-in-polygon over the loaded industrial-zone layer.",
                    limitations=[
                        "Not found in the selected dataset does not mean the site is outside "
                        "every real industrial zone — only that it is outside the zones mapped here."
                    ],
                )
            )
    else:
        findings.append(_unknown_coverage("industrial_zone", checked_at))

    # --- protected area intersection ---------------------------------------------------
    if zones.has_category("protected_area"):
        hits = [p for p, g in zones.by_category("protected_area") if g.intersects(site)]
        if hits:
            for p in hits:
                findings.append(
                    GisFinding(
                        code="protected_area.intersects",
                        category="protected_area",
                        severity="critical",
                        title=f"Site intersects protected area: {p['name']}",
                        value=True,
                        layerId=p["id"],
                        sourceName=p["source_name"],
                        sourceDate=p.get("source_date"),
                        checkedAt=checked_at,
                        methodology="Shapely intersects() (EPSG:4326 coordinates).",
                        limitations=[p.get("notes", "")],
                    )
                )
        else:
            findings.append(
                GisFinding(
                    code="protected_area.no_intersection",
                    category="protected_area",
                    severity="info",
                    title="Site does not intersect any mapped protected area",
                    value=False,
                    layerId="protected_area",
                    sourceName="gadded-gis-layers",
                    checkedAt=checked_at,
                    methodology="Shapely intersects() over the loaded protected-area layer.",
                    limitations=[
                        "Absence in this dataset is not proof the site is unrestricted; "
                        "confirm with the responsible environmental authority."
                    ],
                )
            )
    else:
        findings.append(_unknown_coverage("protected_area", checked_at))

    # --- nearest substation / road distance --------------------------------------------
    findings.append(_nearest_distance_finding(site, site_m, projector, zones, "substation", checked_at))
    findings.append(_nearest_distance_finding(site, site_m, projector, zones, "road", checked_at))

    return findings


_CATEGORY_TO_FINDING = {
    "substation": "substation_distance",
    "road": "road_distance",
}


def _nearest_distance_finding(site, site_m, projector, zones: ZoneLayer, category: str, checked_at: str) -> GisFinding:
    finding_category = _CATEGORY_TO_FINDING[category]
    if not zones.has_category(category):
        return _unknown_coverage(finding_category, checked_at)

    best_p, best_dist = None, math.inf
    for p, g in zones.by_category(category):
        g_m = _to_local(g, projector)
        dist = site_m.distance(g_m)
        if dist < best_dist:
            best_dist, best_p = dist, p

    return GisFinding(
        code=f"{finding_category}.nearest",
        category=finding_category,
        severity="info",
        title=f"Nearest mapped {category}: {best_p['name']}",
        value=round(best_dist, 1),
        unit="m",
        layerId=best_p["id"],
        sourceName=best_p["source_name"],
        sourceDate=best_p.get("source_date"),
        checkedAt=checked_at,
        methodology=(
            "Shapely planar distance in a local equirectangular projection "
            f"({GIS_METHOD_VERSION}); a screening proxy, not authoritative grid-capacity confirmation."
        ),
        limitations=[best_p.get("notes", "")],
    )


def _unknown_coverage(category: str, checked_at: str) -> GisFinding:
    return GisFinding(
        code=f"{category}.unknown",
        category=category,
        severity="unknown",
        title=f"No {category} layer loaded for this site",
        value=None,
        layerId=category,
        sourceName="none",
        checkedAt=checked_at,
        methodology="No matching layer present in the loaded GeoJSON.",
        limitations=["Coverage gap: this check could not be evaluated for this location."],
    )
