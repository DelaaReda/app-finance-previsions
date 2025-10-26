import os
import shutil
import pytest

# Skip the whole E2E collection early when not enabled
if os.getenv('ENABLE_DASH_E2E') != '1':
    pytest.skip('E2E tests are disabled. Set ENABLE_DASH_E2E=1 to enable.', allow_module_level=True)

# Require dash.testing extras
pytest.importorskip('dash.testing')

# Require chromedriver present in PATH when running E2E
if not shutil.which('chromedriver'):
    # Provide a clear skip message so CI/dev knows what to install
    pytest.skip('chromedriver not found in PATH. Install chromedriver (e.g. brew install --cask chromedriver) to run E2E tests.', allow_module_level=True)
