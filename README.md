
# 1) Create a fresh virtualenv
python3 -m venv venv-test
source venv-test/bin/activate

# 2) Install only the minimal deps
pip install -r requirements-minimal.txt

# 3) Install the package in editable mode
pip install -e .

# 4) Run all tests
q
