.PHONY: install test test-spec test-invoice lint format

install:
	pip install -e shared/llm_client --no-build-isolation
	pip install -r services/spec-converterv2/backend/requirements.txt
	pip install -r services/invoice-extractor/backend/requirements.txt

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
