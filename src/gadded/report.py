"""Assemble the final AssessmentResult and render the combined HTML report.

The report is built exclusively from already-computed, typed module outputs — it never
recomputes a calculation. ``assemble_result`` just validates everything fits the
canonical ``AssessmentResult`` contract; ``render_html`` is a pure function of that
result plus a caller-supplied timestamp, so the same inputs always render the same
report (the notebook/caller decides "now", this module stays deterministic and testable).

Vendor discovery is optional: an empty vendor list renders a clear note rather than an
empty-looking gap, and never blocks the rest of the report.
"""

from __future__ import annotations

from jinja2 import Template

from gadded.contracts import (
    AssessmentResult,
    FinancialScenario,
    GisFinding,
    RegulatoryFinding,
    ResultVersions,
    RiskSimulationSummary,
    TechnicalRecommendation,
    VendorCandidate,
)

REPORT_VERSION = "html-report-0.1.0"

DISCLAIMER = (
    "This is a preliminary decision-support assessment. Verify regulatory, engineering, "
    "grid, vendor, and financing information with the responsible authorities and "
    "qualified professionals."
)


def assemble_result(
    run_id: str,
    assessment_id: str,
    status: str,
    technical: TechnicalRecommendation,
    financial: list[FinancialScenario],
    risk: RiskSimulationSummary,
    gis_findings: list[GisFinding],
    regulatory_findings: list[RegulatoryFinding],
    vendors: list[VendorCandidate],
    warnings: list[str],
    versions: ResultVersions,
    generated_artifact_ids: list[str] | None = None,
) -> AssessmentResult:
    """Validate and assemble the canonical AssessmentResult from module outputs."""
    return AssessmentResult(
        runId=run_id,
        assessmentId=assessment_id,
        status=status,
        technical=technical,
        financial=financial,
        risk=risk,
        gisFindings=gis_findings,
        regulatoryFindings=regulatory_findings,
        vendors=vendors,
        warnings=warnings,
        generatedArtifactIds=generated_artifact_ids or [],
        versions=versions,
    )


_STATUS_LABELS = {
    "likely_feasible": "Likely feasible",
    "feasible_with_conditions": "Feasible with conditions",
    "high_risk": "High regulatory/site risk",
    "potentially_ineligible": "Potentially ineligible",
    "insufficient_information": "Insufficient information",
}

_TEMPLATE = Template("""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Gadded Preliminary Assessment — {{ project_name }}</title>
<style>
  body { font-family: -apple-system, Segoe UI, Arial, sans-serif; max-width: 900px;
         margin: 2rem auto; padding: 0 1rem; color: #17211B; background: #F6F7F2; }
  h1, h2 { color: #183B56; }
  .status { display:inline-block; padding: 0.4rem 0.9rem; border-radius: 999px;
            font-weight: 600; border: 1px solid #DCE2D9; }
  .status-likely_feasible { background:#E3F4EA; color:#237A4B; }
  .status-feasible_with_conditions { background:#FFF4D5; color:#B76A00; }
  .status-high_risk, .status-potentially_ineligible { background:#FBE9E9; color:#B93A3A; }
  .status-insufficient_information { background:#EEF1E8; color:#667085; }
  table { border-collapse: collapse; width: 100%; margin: 0.5rem 0 1.5rem; }
  th, td { border: 1px solid #DCE2D9; padding: 0.4rem 0.6rem; text-align: left; font-size: 0.92rem; }
  th { background: #EEF1E8; }
  .disclaimer { background:#FFF4D5; border:1px solid #E7A927; padding:0.8rem 1rem;
                border-radius: 0.75rem; margin: 1.5rem 0; font-size: 0.9rem; }
  .warn { color:#B76A00; } .crit { color:#B93A3A; } .info { color:#237A4B; }
  code { background:#EEF1E8; padding:0.1rem 0.3rem; border-radius:0.3rem; }
  .muted { color:#7A877F; font-size:0.85rem; }
</style>
</head>
<body>

<h1>{{ project_name }}</h1>
<p class="muted">Run {{ run_id }} · Assessment {{ assessment_id }} · Generated {{ generated_at }}</p>
<p><span class="status status-{{ status }}">{{ status_label }}</span></p>

<div class="disclaimer">{{ disclaimer }}</div>

<h2>Technical recommendation</h2>
<table>
  <tr><th>Recommended capacity</th><td>{{ "%.0f"|format(technical.recommendedCapacityKw) }} kW
      (physical roof maximum: {{ "%.0f"|format(technical.physicalMaximumKw) }} kW)</td></tr>
  <tr><th>Annual PV generation</th><td>{{ "{:,.0f}".format(technical.annualGenerationKwh) }} kWh</td></tr>
  <tr><th>Annual factory load</th><td>{{ "{:,.0f}".format(technical.annualLoadKwh) }} kWh</td></tr>
  <tr><th>Self-consumption ratio</th><td>{{ "%.1f"|format(technical.selfConsumptionRatio*100) }}%</td></tr>
  <tr><th>Self-sufficiency ratio</th><td>{{ "%.1f"|format(technical.selfSufficiencyRatio*100) }}%</td></tr>
  <tr><th>Imported / exported energy</th><td>{{ "{:,.0f}".format(technical.annualImportedKwh) }} kWh
      imported / {{ "{:,.0f}".format(technical.annualExportedKwh) }} kWh exported</td></tr>
  <tr><th>Roof area required</th><td>{{ "%.0f"|format(technical.roofAreaRequiredM2) }} m²</td></tr>
  <tr><th>Binding constraint</th><td>{{ technical.bindingConstraints|join(", ") }}</td></tr>
  <tr><th>Sizing objective</th><td><code>{{ technical.objectiveName }}</code>
      over {{ technical.evaluatedCapacitiesKw|length }} evaluated candidate sizes</td></tr>
</table>

<h2>Financial scenarios</h2>
<table>
  <tr><th>Scenario</th><th>Capex</th><th>Year-1 net savings</th><th>NPV</th><th>IRR</th>
      <th>Simple payback</th><th>Discounted payback</th><th>Monthly loan</th></tr>
  {% for s in financial %}
  <tr>
    <td>{{ s.scenario }}</td>
    <td>{{ "{:,.0f}".format(s.capexEgp) }} EGP</td>
    <td>{{ "{:,.0f}".format(s.yearOneSavingsEgp) }} EGP</td>
    <td>{{ "{:,.0f}".format(s.npvEgp) }} EGP</td>
    <td>{{ "%.1f%%"|format(s.irrPct) if s.irrPct is not none else "n/a" }}</td>
    <td>{{ "%.1f yr"|format(s.simplePaybackYears) if s.simplePaybackYears is not none else "not recovered" }}</td>
    <td>{{ "%.1f yr"|format(s.discountedPaybackYears) if s.discountedPaybackYears is not none else "not recovered" }}</td>
    <td>{{ "{:,.0f} EGP".format(s.monthlyLoanPaymentEgp) if s.monthlyLoanPaymentEgp else "n/a" }}</td>
  </tr>
  {% endfor %}
</table>
<p class="muted">Nominal cash flows; includes O&M, tariff escalation, panel degradation. Excludes tax,
general inflation adjustment, inverter replacement, and residual value.</p>

<h2>Risk (Monte Carlo, {{ risk.runCount }} runs, seed {{ risk.seed }})</h2>
<table>
  <tr><th></th><th>P10</th><th>P50 (median)</th><th>P90</th></tr>
  <tr><th>NPV (EGP)</th>
      <td>{{ "{:,.0f}".format(risk.npvP10Egp) }}</td>
      <td>{{ "{:,.0f}".format(risk.npvP50Egp) }}</td>
      <td>{{ "{:,.0f}".format(risk.npvP90Egp) }}</td></tr>
  <tr><th>Payback (years)</th>
      <td>{{ "%.1f"|format(risk.paybackP10Years) if risk.paybackP10Years is not none else "n/a" }}</td>
      <td>{{ "%.1f"|format(risk.paybackP50Years) if risk.paybackP50Years is not none else "n/a" }}</td>
      <td>{{ "%.1f"|format(risk.paybackP90Years) if risk.paybackP90Years is not none else "n/a" }}</td></tr>
</table>
{% if risk.probabilityTargetPaybackPct is not none %}
<p>Probability of meeting the target payback: <strong>{{ "%.1f"|format(risk.probabilityTargetPaybackPct) }}%</strong></p>
{% endif %}
<h3>Top sensitivity drivers</h3>
<table>
  <tr><th>Variable</th><th>Relative influence</th></tr>
  {% for d in risk.topSensitivityDrivers %}
  <tr><td>{{ d.variable }}</td><td>{{ "%.0f%%"|format(d.influence*100) }}</td></tr>
  {% endfor %}
</table>

<h2>Site screening</h2>
<table>
  <tr><th>Category</th><th>Severity</th><th>Title</th><th>Value</th><th>Source</th></tr>
  {% for g in gis_findings %}
  <tr>
    <td>{{ g.category }}</td>
    <td class="{{ 'crit' if g.severity=='critical' else ('warn' if g.severity=='warning' else 'info') }}">{{ g.severity }}</td>
    <td>{{ g.title }}</td>
    <td>{{ g.value if g.value is not none else "—" }}{{ " " + g.unit if g.unit }}</td>
    <td class="muted">{{ g.sourceName }}</td>
  </tr>
  {% endfor %}
</table>

<h2>Regulatory findings</h2>
{% for f in regulatory_findings %}
<table>
  <tr><th>{{ f.title }}</th><td class="{{ 'crit' if f.severity=='critical' else ('warn' if f.severity=='warning' else 'info') }}">
      {{ f.conclusion }} · {{ f.severity }} · confidence {{ f.confidence }}</td></tr>
  <tr><td colspan="2">{{ f.explanation }}</td></tr>
  {% if f.requiredDocuments %}<tr><th>Required documents</th><td>{{ f.requiredDocuments|join(", ") }}</td></tr>{% endif %}
  {% if f.citations %}
  <tr><th>Citations</th><td>
    {% for c in f.citations %}
      {{ c.authority }} — <em>{{ c.documentTitle }}</em>{% if c.section %}, §{{ c.section }}{% endif %}{% if c.effectiveDate %} (effective {{ c.effectiveDate }}){% endif %}<br>
    {% endfor %}
  </td></tr>
  {% endif %}
  <tr><td colspan="2" class="muted">Verification required: {{ "yes" if f.verificationRequired else "no" }}</td></tr>
</table>
{% else %}
<p class="muted">No regulatory findings were produced for this run.</p>
{% endfor %}

<h2>Vendor candidates</h2>
{% if vendors %}
<table>
  <tr><th>Name</th><th>Fit</th><th>Evidence</th><th>Status</th></tr>
  {% for v in vendors %}
  <tr>
    <td>{{ v.name }}<br><span class="muted"><a href="{{ v.websiteUrl }}">{{ v.websiteUrl }}</a></span></td>
    <td>{{ v.fitExplanation }}</td>
    <td>{% for e in v.evidence %}<a href="{{ e.url }}">{{ e.title }}</a><br>{% endfor %}</td>
    <td>{{ v.verificationStatus }}</td>
  </tr>
  {% endfor %}
</table>
{% else %}
<p class="muted">No vendor candidates found evidence for in this run. Vendor discovery is
independent of the technical/financial result above and can be re-run separately.</p>
{% endif %}
<p class="muted">Vendor leads require independent verification before use.</p>

<h2>Sources, assumptions, and versions</h2>
<table>
  <tr><th>Code version</th><td><code>{{ versions.code }}</code></td></tr>
  <tr><th>Assumption set</th><td><code>{{ versions.assumptionSet }}</code></td></tr>
  <tr><th>Load model</th><td><code>{{ versions.loadModel }}</code></td></tr>
  <tr><th>PV model</th><td><code>{{ versions.pvModel }}</code></td></tr>
  <tr><th>Regulatory prompt</th><td><code>{{ versions.regulatoryPrompt }}</code></td></tr>
  <tr><th>Vendor prompt</th><td><code>{{ versions.vendorPrompt }}</code></td></tr>
</table>

{% if warnings %}
<h2>Warnings</h2>
<ul>{% for w in warnings %}<li class="warn">{{ w }}</li>{% endfor %}</ul>
{% endif %}

<div class="disclaimer">{{ disclaimer }}</div>

</body>
</html>
""")


def render_html(
    result: AssessmentResult,
    project_name: str,
    generated_at: str,
) -> str:
    """Render the combined report as a self-contained HTML string. Pure and deterministic."""
    return _TEMPLATE.render(
        project_name=project_name,
        run_id=result.runId,
        assessment_id=result.assessmentId,
        generated_at=generated_at,
        status=result.status,
        status_label=_STATUS_LABELS.get(result.status, result.status),
        disclaimer=DISCLAIMER,
        technical=result.technical,
        financial=result.financial,
        risk=result.risk,
        gis_findings=result.gisFindings,
        regulatory_findings=result.regulatoryFindings,
        vendors=result.vendors,
        versions=result.versions,
        warnings=result.warnings,
    )
