run: .venv
	source .venv/bin/activate &&\
	./main.py $(ARGS)
.venv: # should only run once
	curl https://openrouter.ai/api/v1/models | python -m json.tool > .models
	python -m venv .venv
	source .venv/bin/activate &&\
	pip install -r requirements.txt

.PHONY: run