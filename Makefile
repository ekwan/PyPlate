PYTHONPATH := $(shell pwd)

docs: pyplate/pyplate.py
	pdoc pyplate/pyplate.py -d google -o docs/ --no-include-undocumented

test:
	pytest tests

coverage:
	pytest --cov=pyplate --cov-report html tests

clean:
	rm -rf docs