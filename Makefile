run: .venv .model
	source .venv/bin/activate &&\
	./main.py $(ARGS)
.venv: # should only run once
	python -m venv .venv
	source .venv/bin/activate &&\
	pip install -r requirements.txt
.models:
	curl https://openrouter.ai/api/v1/models | python -m json.tool > .models

clean:
	rm -f .models
	rm -rf .venv

.PHONY: run clean