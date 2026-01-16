#!/bin/bash
# Integration test script for clipboard history feature

echo "======================================"
echo "Clipboard History Integration Test"
echo "======================================"
echo ""

# Test 1: Stats
echo "Test 1: Clipboard Stats"
ishell -c "clipboard stats"
echo ""

# Test 2: History
echo "Test 2: Clipboard History"
ishell -c "clipboard history"
echo ""

# Test 3: Search
echo "Test 3: Search for 'github'"
ishell -c "clipboard search github"
echo ""

# Test 4: Natural language query
echo "Test 4: Natural Language Query"
ishell -c "show me clipboard history"
echo ""

echo "======================================"
echo "All tests completed!"
echo "======================================"
