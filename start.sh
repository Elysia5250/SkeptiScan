#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

echo "=== SkeptiScan v2.0 Quick Start ==="

# 后端依赖
echo "[1/3] Installing backend dependencies..."
cd backend
[ ! -d venv ] && python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -q
cd ..

# 前端构建
echo "[2/3] Building frontend..."
cd frontend
npm install --silent
npm run build --silent
cd ..

# 启动
echo "[3/3] Starting server at http://localhost:8000"
echo ""
cd backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
