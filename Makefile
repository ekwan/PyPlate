PYTHONPATH := $(shell pwd)

docs:
	pdoc pyplate/pyplate.py -d google -o docs/ --no-include-undocumented

test:
	pytest tests

clean:
	rm -rf docs