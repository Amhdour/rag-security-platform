.PHONY: evidence evidence-demo evidence-step evidence-step-demo demo provenance-check adapter-validate adapter-smoke adapter-ci adapter-integrity adapter-retention adapter-retention-apply adapter-health control-matrix evidence-summary launch-gate-bridge

evidence:
	cd integration-adapter && python -m integration_adapter.evidence_pipeline

evidence-demo:
	cd integration-adapter && python -m integration_adapter.evidence_pipeline --demo

demo:
	cd integration-adapter && python -m integration_adapter.demo_scenario


evidence-step:
	cd integration-adapter && python -m integration_adapter.collect_from_onyx
	cd integration-adapter && python -m integration_adapter.generate_artifacts
	cd integration-adapter && python -m integration_adapter.run_launch_gate

evidence-step-demo:
	cd integration-adapter && python -m integration_adapter.collect_from_onyx --demo
	cd integration-adapter && python -m integration_adapter.generate_artifacts --demo
	cd integration-adapter && python -m integration_adapter.run_launch_gate


provenance-check:
	python scripts/validate_upstream_provenance_lock.py

adapter-validate:
	cd integration-adapter && python -m integration_adapter.validate_config

adapter-smoke:
	cd integration-adapter && python -m integration_adapter.ci_smoke

adapter-ci:
	cd integration-adapter && python -m integration_adapter.validate_config
	cd integration-adapter && python -m integration_adapter.ci_smoke
	cd integration-adapter && python -m pytest -q

adapter-integrity:
	cd integration-adapter && python -m integration_adapter.verify_artifact_integrity

adapter-retention:
	cd integration-adapter && python -m integration_adapter.artifact_retention --dry-run

adapter-retention-apply:
	cd integration-adapter && python -m integration_adapter.artifact_retention --apply

adapter-health:
	cd integration-adapter && python -m integration_adapter.health_report --format text

control-matrix:
	cd integration-adapter && python -m integration_adapter.control_matrix --output-doc ../docs/control-matrix.md

evidence-summary:
	cd integration-adapter && python -m integration_adapter.evidence_report --artifacts-root artifacts/logs --output-md ../docs/evidence-summary.md --output-json artifacts/logs/evidence-summary.json --output-html artifacts/logs/evidence-summary.html

launch-gate-bridge:
	cd integration-adapter && python -m integration_adapter.launch_gate_bridge --artifacts-root artifacts/logs --output-json ../docs/launch-gate-bridge.example.json --output-md ../docs/launch-gate-bridge.example.md
