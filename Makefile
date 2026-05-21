PIP = pip
STREAMLIT = streamlit
APP_FILE = app.py

install:
	$(PIP) install -r requirements.txt
run:
	$(STREAMLIT) run $(APP_FILE)