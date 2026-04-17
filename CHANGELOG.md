# Changelog

All notable changes to pyRE are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

## [1.0.0] — 2026-04-17

### Added
- Full CI/CD pipeline: GitHub Actions for lint, typecheck, test, release, and docs
- Pre-commit hooks: ruff, mypy, file hygiene
- mypy strict type checking; `py.typed` PEP 561 marker
- ≥80% test coverage enforced via pytest-cov
- DFA `Simulation` engine with Monte Carlo frequency/severity sampling, TVaR/VaR capital, investment return, profit commission, retrocession, and required premium
- `SeverityFit` and `FrequencyFit` distribution fitting with MLE/MOM estimators
- `ModellingAssumptions` dataclass for centralised assumption management
- `Triangle.get_selected_development_pattern()` for BurnCostModel integration
- Parallelogram earned percentage method on `Exposure` for aggregate exposures
- `ExposureModel.calculate_exposure_rate()` and `calculate_ilf_adjusted_rate()`
- `SimulationResults.save()` JSON serialisation
- `CredibilityWeight` class with five credibility methods (limited fluctuation, Bühlmann, Bühlmann-Straub, greatest accuracy, Bayesian)
- mkdocs documentation site

### Changed
- All classes converted from Java-style property boilerplate to `@dataclass`
- Package directories renamed: `Models/` → `models/`, `Experience/` → `experience/`, `Exposure/` → `exposure/`, `AggregateFeatures/` → `aggregate/`
- All enumerations consolidated into `pyre/enums.py`
- `ClaimTriggerBasis.to_claim_year_type()` replaces module-level dict mapping
- No backward compatibility — clean break from 0.x series

### Fixed
- `Trending.trend_exposures` and `trend_claims`: direction-aware multiply/divide
- `Triangle.from_claims`: wrong attribute path for `modelling_year`; `dev_history` iteration
- `ExposureModel._calculate_single_exposure_share`: share calculation was inside wrong `else` branch
- `Exposure.earned_exposure_value`: EARNED/WRITTEN logic was inverted
- `Exposure._earned_pct`: negative values before start date now clamped to 0

## [0.0.1] — 2025-01-01

### Added
- Initial beta release
