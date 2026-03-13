.PHONY: evidence evidence-demo demo

evidence:
	cd integration-adapter && python -m integration_adapter.evidence_pipeline

evidence-demo:
	cd integration-adapter && python -m integration_adapter.evidence_pipeline --demo

demo:
	cd integration-adapter && python -m integration_adapter.demo_scenario
