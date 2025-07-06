#!/bin/bash
set -e

create_uploads_dir() {
    if [ ! -d "uploads" ]; then
        mkdir -p uploads
    fi
}

run_app() {
    
    export FLASK_DEBUG=true
    python run.py
}

create_uploads_dir    
run_app
