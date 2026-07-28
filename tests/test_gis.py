"""GIS: known-point checks, distance methodology, coverage-gap behavior."""

from pathlib import Path

import pytest

from gadded.gis import ZoneLayer, load_zones, screen_site

ROOT = Path(__file__).resolve().parents[1]
ZONES_PATH = ROOT / "data" / "zones.geojson"


def _by_code(findings, code):
    return next(f for f in findings if f.code == code)


def test_golden_site_is_inside_10th_ramadan_zone() -> None:
    zones = load_zones(ZONES_PATH)
    findings = screen_site(30.3203, 31.7466, zones)
    inside = _by_code(findings, "industrial_zone.inside")
    assert inside.severity == "info"
    assert "10th of Ramadan" in inside.value


def test_golden_site_does_not_intersect_protected_area() -> None:
    zones = load_zones(ZONES_PATH)
    findings = screen_site(30.3203, 31.7466, zones)
    protected = _by_code(findings, "protected_area.no_intersection")
    assert protected.severity == "info"
    assert protected.value is False


def test_point_inside_protected_area_is_critical() -> None:
    zones = load_zones(ZONES_PATH)
    # inside the synthetic protected polygon (31.80-31.83, 30.335-30.360)
    findings = screen_site(30.345, 31.815, zones)
    hit = _by_code(findings, "protected_area.intersects")
    assert hit.severity == "critical"
    assert hit.value is True


def test_point_outside_every_zone_is_not_found_not_absent() -> None:
    zones = load_zones(ZONES_PATH)
    # far from both industrial zones and the protected polygon
    findings = screen_site(28.0, 33.0, zones)
    zone_finding = _by_code(findings, "industrial_zone.not_found")
    assert zone_finding.severity == "warning"
    assert "does not mean" in zone_finding.limitations[0]


def test_second_zone_recognized() -> None:
    zones = load_zones(ZONES_PATH)
    findings = screen_site(29.900, 30.930, zones)  # inside 6th of October zone
    inside = _by_code(findings, "industrial_zone.inside")
    assert "6th of October" in inside.value


def test_distance_findings_present_and_positive() -> None:
    zones = load_zones(ZONES_PATH)
    findings = screen_site(30.3203, 31.7466, zones)
    sub = _by_code(findings, "substation_distance.nearest")
    road = _by_code(findings, "road_distance.nearest")
    assert sub.unit == "m" and sub.value >= 0
    assert road.unit == "m" and road.value >= 0
    # golden site sits inside the real 10th of Ramadan industrial zone; real
    # OSM substations/roads in the wider city area should be within ~10km
    assert sub.value < 10000
    assert road.value < 10000


def test_missing_layer_returns_unknown_not_clear() -> None:
    empty = ZoneLayer(manifest={}, features=[])
    findings = screen_site(30.30, 31.74, empty)
    for f in findings:
        assert f.severity == "unknown"
        assert f.value is None


def test_zones_manifest_labels_mixed_real_and_synthetic_sources() -> None:
    zones = load_zones(ZONES_PATH)
    assert zones.manifest["source_class"] == "MIXED"
    provenance_lower = zones.manifest["provenance"].lower()
    assert "openstreetmap" in provenance_lower
    assert "wdpa" in provenance_lower
    assert "synthetic" in provenance_lower


def test_real_protected_areas_loaded_from_wdpa() -> None:
    zones = load_zones(ZONES_PATH)
    wdpa_features = [
        p for p, _ in zones.by_category("protected_area")
        if p["source_class"] == "OFFICIAL"
    ]
    assert len(wdpa_features) > 40  # 47 real WDPA Egypt sites expected


def test_real_industrial_zone_and_road_loaded_from_osm() -> None:
    zones = load_zones(ZONES_PATH)
    industrial_official = [
        p for p, _ in zones.by_category("industrial_zone") if p["source_class"] == "OFFICIAL"
    ]
    road_official = [p for p, _ in zones.by_category("road") if p["source_class"] == "OFFICIAL"]
    assert len(industrial_official) == 1
    assert len(road_official) == 1
