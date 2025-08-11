#!/bin/bash

cleanup() {
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

if [ ! -d "frontend/node_modules" ]; then
    cd frontend
    npm install
    cd ..
fi

cd backend
python run.py &
BACKEND_PID=$!
cd ..


cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

wait
