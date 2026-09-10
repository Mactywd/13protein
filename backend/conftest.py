import sys
import os

# Ensure the backend root is on sys.path so tests in subdirectories
# (e.g. tests/handlers/) can import backend modules directly.
sys.path.insert(0, os.path.dirname(__file__))
