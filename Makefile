.PHONY: test test-spec test-invoice lint format

test:
	pytest services/invoice-extractor/ -v
	pytest services/spec-converterv2/ -v

test-spec:
	pytest services/spec-converterv2/ -v

test-invoice:
	pytest services/invoice-extractor/ -v

lint:
	ruff check services/

format:
	ruff format services/
