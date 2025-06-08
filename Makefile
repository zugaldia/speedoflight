run:
	python3 launch.py

lint:
	ruff check speedoflight/

format-check:
	ruff format --check speedoflight/

format-diff:
	ruff format --diff speedoflight/

typecheck:
	mypy speedoflight/
