ifeq ($(ARGS), ) # if empty, choose some defaults
ARGS := in/in.pdf cognitivecomputations/dolphin3.0-r1-mistral-24b:free
endif

run: .venv .models.json
	source .venv/bin/activate &&\
	./main.py $(ARGS)
.venv: # should only run once
	python -m venv .venv
	source .venv/bin/activate &&\
	pip install -r requirements.txt
.models.json:
	curl https://openrouter.ai/api/v1/models | python -m json.tool > .models.json

clean:
	rm -f .models.json
	rm -rf .venv

.PHONY: run clean