#!/data/data/com.termux/files/usr/bin/bash
set -e

echo "=========================================================="
echo "🚀 Termux Voicecall Agent Automatic Setup"
echo "=========================================================="

echo "📦 Step 1: Installing pre-compiled Android wheel for pydantic-core..."
pip install pydantic-core --extra-index-url https://eutalix.github.io/android-pydantic-core/ || \
pip install pydantic-core --extra-index-url https://termux-user-repository.github.io/pypi/ || \
(pkg install rust -y && pip install pydantic-core)

echo "📦 Step 2: Installing remaining Python packages..."
pip install -r requirements.txt

echo "=========================================================="
echo "✅ All packages installed successfully!"
echo "🚀 Launching Voicecall Agent on your phone..."
echo "=========================================================="
python main.py
