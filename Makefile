# Makefile for Finance Copilot API

# Variables
APP_NAME := src.api.main
UVICORN := uvicorn

# Run the API
run:
	$(UVICORN) $(APP_NAME):app --reload

# Run tests (example - adapt to your testing framework)
test:
	# Add your test command here, e.g., pytest tests/
	@echo "No tests defined yet.  Please add tests and update the 'test' target in the Makefile."

# Format code (example - adapt to your formatting tool)
format:
	# Add your format command here, e.g., black .
	@echo "No formatting defined yet. Please add a formatting tool and update the 'format' target in the Makefile."
