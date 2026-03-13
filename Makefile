.PHONY: evidence evidence-demo evidence-step evidence-step-demo demo provenance-check adapter-validate adapter-smoke adapter-ci adapter-integrity

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
