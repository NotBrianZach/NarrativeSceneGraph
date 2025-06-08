ifeq ($(ARGS), ) # if empty, choose some defaults
ARGS := in/CrookedHouse.pdf deepseek/deepseek-r1-distill-llama-70b:free
endif

run: .venv .models.json
	source .venv/bin/activate &&\
	./main.py $(ARGS)
.venv: # should only run once
	python3 -m venv .venv
	source .venv/bin/activate &&\
	pip install -r requirements.txt
	if [[ ! "$(command -v dot)" ]]; then echo "NOTE: remember to install graphviz (https://www.graphviz.org/)."; fi
	echo "What's your OpenRouter API key?" &&\
	read token &&\
	echo $$token > .API_TOKEN
.models.json:
	curl https://openrouter.ai/api/v1/models | python3 -m json.tool > .models.json

clean:
	rm -f .models.json
	rm -rf .venv

.PHONY: run clean