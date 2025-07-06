# backend/assets.py
from flask_assets import Bundle

# Define a JavaScript bundle. We will add more files to this later.
# The order matters: main.js should come last as it executes the initializers.
js_main_bundle = Bundle(
    'js/breadcrumb_ui.js',
    'js/inline_table_edit.js',      # <-- FIX: Added for inline editing
    'js/usecase_overview.js',       # <-- FIX: Added for use case filtering
    'js/ptps_overview.js',          # NEW: Added for Process Steps page filtering
    'js/main.js',
    filters='jsmin',
    output='gen/app.%(version)s.js'
)

# Define a CSS bundle.
css_bundle = Bundle(
    'css/style.css',
    filters='cssmin',
    output='gen/style.%(version)s.css'
)