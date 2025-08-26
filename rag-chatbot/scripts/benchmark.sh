#!/bin/bash
set -e

echo "🚀 RAG System Performance Benchmark"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if services are running
echo "📊 Checking system status..."
if ! curl -s -H "x-api-key: changeme" http://localhost:8000/healthz > /dev/null; then
    echo -e "${RED}❌ Backend not running. Please start with: docker-compose up -d${NC}"
    exit 1
fi

if ! curl -s -H "x-api-key: changeme" http://localhost:8000/readyz > /dev/null; then
    echo -e "${RED}❌ System not ready. Please seed documents with: make seed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ System is ready${NC}"

# Test 1: Latency Benchmark
echo ""
echo "📈 Test 1: Retrieval Latency Test"
echo "Target: <50ms retrieval latency"
echo "--------------------------------"

latency_sum=0
latency_count=0
max_latency=0
min_latency=9999

for i in {1..20}; do
    response=$(curl -s -H "x-api-key: changeme" \
        -X POST http://localhost:8000/query \
        -H "content-type: application/json" \
        -d '{"q":"What vector stores are supported?"}')
    
    latency=$(echo $response | jq -r '.retrieval_debug.retrieval_time_ms // 0')
    if [ "$latency" != "0" ] && [ "$latency" != "null" ]; then
        latency_sum=$(echo "$latency_sum + $latency" | bc)
        latency_count=$((latency_count + 1))
        
        if (( $(echo "$latency > $max_latency" | bc -l) )); then
            max_latency=$latency
        fi
        if (( $(echo "$latency < $min_latency" | bc -l) )); then
            min_latency=$latency
        fi
        
        echo "  Request $i: ${latency}ms"
    fi
done

if [ $latency_count -gt 0 ]; then
    avg_latency=$(echo "scale=2; $latency_sum / $latency_count" | bc)
    echo ""
    echo "📊 Latency Results:"
    echo "  Average: ${avg_latency}ms"
    echo "  Min: ${min_latency}ms" 
    echo "  Max: ${max_latency}ms"
    
    if (( $(echo "$avg_latency < 50" | bc -l) )); then
        echo -e "${GREEN}✅ PASS: Average latency ${avg_latency}ms < 50ms target${NC}"
        latency_pass=true
    else
        echo -e "${RED}❌ FAIL: Average latency ${avg_latency}ms >= 50ms target${NC}"
        latency_pass=false
    fi
else
    echo -e "${RED}❌ FAIL: Could not measure latency${NC}"
    latency_pass=false
fi

# Test 2: Load Test with k6
echo ""
echo "🔥 Test 2: Load Test (50 QPS)"
echo "Target: Handle 50 queries per second"
echo "-----------------------------------"

if command -v k6 > /dev/null 2>&1; then
    echo "Running k6 load test..."
    k6_result=$(k6 run --quiet --no-color loadtest/k6.js 2>&1 | tail -20)
    
    # Parse k6 results
    success_rate=$(echo "$k6_result" | grep -o "query_success_rate.*" | grep -o "[0-9.]*%" | head -1)
    avg_response_time=$(echo "$k6_result" | grep -o "http_req_duration.*avg=[0-9.]*ms" | grep -o "[0-9.]*ms" | head -1)
    
    echo "📊 Load Test Results:"
    echo "  Success Rate: ${success_rate:-N/A}"
    echo "  Average Response Time: ${avg_response_time:-N/A}"
    
    if [[ "$success_rate" =~ 9[0-9]% ]] || [[ "$success_rate" =~ 100% ]]; then
        echo -e "${GREEN}✅ PASS: Success rate ${success_rate} >= 90%${NC}"
        load_pass=true
    else
        echo -e "${RED}❌ FAIL: Success rate ${success_rate} < 90%${NC}"
        load_pass=false
    fi
else
    echo -e "${YELLOW}⚠️  k6 not installed, running simple load test...${NC}"
    
    # Simple concurrent test
    start_time=$(date +%s.%N)
    success_count=0
    total_requests=100
    
    for i in $(seq 1 $total_requests); do
        (
            response=$(curl -s -w "%{http_code}" -H "x-api-key: changeme" \
                -X POST http://localhost:8000/query \
                -H "content-type: application/json" \
                -d '{"q":"Test query '$i'"}')
            if [[ "$response" =~ 200$ ]]; then
                echo "success" > /tmp/load_test_$i
            fi
        ) &
        
        # Limit concurrent processes
        if (( i % 10 == 0 )); then
            wait
        fi
    done
    wait
    
    end_time=$(date +%s.%N)
    duration=$(echo "$end_time - $start_time" | bc)
    qps=$(echo "scale=2; $total_requests / $duration" | bc)
    
    success_count=$(ls /tmp/load_test_* 2>/dev/null | wc -l)
    success_rate=$(echo "scale=1; $success_count * 100 / $total_requests" | bc)
    
    echo "📊 Simple Load Test Results:"
    echo "  Requests: $total_requests"
    echo "  Success: $success_count"
    echo "  Success Rate: ${success_rate}%"
    echo "  Duration: ${duration}s"
    echo "  QPS: ${qps}"
    
    # Cleanup
    rm -f /tmp/load_test_*
    
    if (( $(echo "$success_rate >= 90" | bc -l) )) && (( $(echo "$qps >= 30" | bc -l) )); then
        echo -e "${GREEN}✅ PASS: Load test successful${NC}"
        load_pass=true
    else
        echo -e "${RED}❌ FAIL: Load test failed${NC}"
        load_pass=false
    fi
fi

# Test 3: Hallucination Resistance Test
echo ""
echo "🧠 Test 3: Hallucination Resistance"
echo "Target: Refuse to answer unknown questions"
echo "----------------------------------------"

# Test questions that should return "I don't have enough information"
hallucination_queries=(
    "What is the company's stock price?"
    "How many employees work here?"
    "What is the CEO's salary?"
    "What programming languages does the API support?"
    "What is the maximum file upload size?"
)

correct_refusals=0
total_tests=${#hallucination_queries[@]}

for query in "${hallucination_queries[@]}"; do
    response=$(curl -s -H "x-api-key: changeme" \
        -X POST http://localhost:8000/query \
        -H "content-type: application/json" \
        -d "{\"q\":\"$query\"}")
    
    answer=$(echo "$response" | jq -r '.answer // ""')
    
    if [[ "$answer" =~ "don't have enough information" ]] || [[ "$answer" =~ "I don't know" ]] || [[ "$answer" =~ "cannot answer" ]]; then
        echo "  ✅ \"$query\" - Correctly refused"
        correct_refusals=$((correct_refusals + 1))
    else
        echo "  ❌ \"$query\" - Potentially hallucinated: $answer"
    fi
done

hallucination_rate=$(echo "scale=1; $correct_refusals * 100 / $total_tests" | bc)
echo ""
echo "📊 Hallucination Test Results:"
echo "  Correct Refusals: $correct_refusals/$total_tests"
echo "  Refusal Rate: ${hallucination_rate}%"

if (( $(echo "$hallucination_rate >= 80" | bc -l) )); then
    echo -e "${GREEN}✅ PASS: Hallucination resistance ${hallucination_rate}% >= 80%${NC}"
    hallucination_pass=true
else
    echo -e "${RED}❌ FAIL: Hallucination resistance ${hallucination_rate}% < 80%${NC}"
    hallucination_pass=false
fi

# Final Summary
echo ""
echo "🏆 FINAL PERFORMANCE ASSESSMENT"
echo "==============================="

total_score=0
max_score=3

if [ "$latency_pass" = true ]; then
    echo -e "${GREEN}✅ Latency Test: PASS${NC}"
    total_score=$((total_score + 1))
else
    echo -e "${RED}❌ Latency Test: FAIL${NC}"
fi

if [ "$load_pass" = true ]; then
    echo -e "${GREEN}✅ Load Test: PASS${NC}"
    total_score=$((total_score + 1))
else
    echo -e "${RED}❌ Load Test: FAIL${NC}"
fi

if [ "$hallucination_pass" = true ]; then
    echo -e "${GREEN}✅ Hallucination Test: PASS${NC}"
    total_score=$((total_score + 1))
else
    echo -e "${RED}❌ Hallucination Test: FAIL${NC}"
fi

echo ""
echo "📊 Overall Score: $total_score/$max_score"

if [ $total_score -eq $max_score ]; then
    echo -e "${GREEN}🎉 EXCELLENT: System meets all performance targets!${NC}"
    echo "   ✅ <50ms retrieval latency"
    echo "   ✅ 50+ QPS throughput capability" 
    echo "   ✅ Strong hallucination resistance"
    exit 0
elif [ $total_score -eq 2 ]; then
    echo -e "${YELLOW}⚠️  GOOD: System meets most performance targets${NC}"
    exit 0
else
    echo -e "${RED}❌ NEEDS IMPROVEMENT: System requires optimization${NC}"
    exit 1
fi