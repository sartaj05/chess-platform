#!/usr/bin/env sh
set -eu
mkdir -p static/vendor/bootstrap static/vendor/htmx static/vendor/alpine
fetch_file(){ url="$1"; out="$2"; [ -s "$out" ] || curl -fsSL "$url" -o "$out"; }
fetch_file "https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css" "static/vendor/bootstrap/bootstrap.min.css"
fetch_file "https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js" "static/vendor/bootstrap/bootstrap.bundle.min.js"
fetch_file "https://unpkg.com/htmx.org@2.0.7/dist/htmx.min.js" "static/vendor/htmx/htmx.min.js"
fetch_file "https://unpkg.com/alpinejs@3.14.9/dist/cdn.min.js" "static/vendor/alpine/alpine.min.js"
