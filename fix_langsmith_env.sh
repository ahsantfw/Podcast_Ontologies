#!/bin/bash
# Fix LangSmith environment variables in .env file
# LangSmith uses LANGCHAIN_ prefix, not LANGSMITH_

cd "$(dirname "$0")"

if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    exit 1
fi

echo "🔧 Fixing LangSmith environment variables..."

# Backup .env
cp .env .env.backup
echo "✅ Created backup: .env.backup"

# Fix variable names
sed -i 's/^LANGSMITH_TRACING=/LANGCHAIN_TRACING_V2=/' .env
sed -i 's/^LANGSMITH_API_KEY=/LANGCHAIN_API_KEY=/' .env
sed -i 's/^LANGSMITH_PROJECT=/LANGCHAIN_PROJECT=/' .env

# Remove LANGSMITH_ENDPOINT (not needed, uses default)
sed -i '/^LANGSMITH_ENDPOINT=/d' .env

# Ensure LANGCHAIN_TRACING_V2 is set to true
if ! grep -q "^LANGCHAIN_TRACING_V2=" .env; then
    echo "LANGCHAIN_TRACING_V2=true" >> .env
fi

# Ensure value is true (not just set)
sed -i 's/^LANGCHAIN_TRACING_V2=.*/LANGCHAIN_TRACING_V2=true/' .env

echo "✅ Fixed environment variables!"
echo ""
echo "📋 Updated variables:"
grep -E "^LANGCHAIN_" .env || echo "  (none found)"
echo ""
echo "🧪 Test with: python test_langsmith.py"

