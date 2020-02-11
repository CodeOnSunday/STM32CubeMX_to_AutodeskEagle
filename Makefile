.PHONY: build run

run:
	pipenv run python main.py

build:
	pipenv run python setup.py build