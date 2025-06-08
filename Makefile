run:
	python3 launch.py

lint:
	ruff check speedoflight/

typecheck:
	mypy speedoflight/
