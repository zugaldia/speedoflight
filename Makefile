run:
	python3 launch.py

run-light:
	GTK_THEME=Adwaita:light python3 launch.py

run-dark:
	GTK_THEME=Adwaita:dark python3 launch.py

lint:
	ruff check speedoflight/

format-check:
	ruff format --check speedoflight/

format-diff:
	ruff format --diff speedoflight/
