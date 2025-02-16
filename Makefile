run: .venv
	source .venv/bin/activate &&\
	./main.py
.venv: # should only run once
	chmod +x main.py
	python -m venv .venv
	source .venv/bin/activate &&\
	pip install -r requirements.txt