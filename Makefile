.PHONY: evidence evidence-demo evidence-step evidence-step-demo demo

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
