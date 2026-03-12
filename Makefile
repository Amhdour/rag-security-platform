.PHONY: evidence demo

evidence:
	cd integration-adapter && python -m integration_adapter.generate_artifacts

demo:
	cd integration-adapter && python -m integration_adapter.demo_scenario
