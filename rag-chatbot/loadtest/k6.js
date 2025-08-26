import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const retrievalLatency = new Trend('retrieval_latency_ms');
const successRate = new Rate('query_success_rate');

export const options = {
  scenarios: {
    // Test 50 QPS target performance
    high_load: {
      executor: 'constant-arrival-rate',
      rate: 50, // 50 requests per second
      timeUnit: '1s',
      duration: '2m',
      preAllocatedVUs: 10,
      maxVUs: 100,
    },
    // Stress test to find breaking point
    stress_test: {
      executor: 'ramping-arrival-rate',
      startRate: 10,
      timeUnit: '1s',
      stages: [
        { duration: '30s', target: 20 },
        { duration: '30s', target: 50 },
        { duration: '1m', target: 100 },
        { duration: '30s', target: 150 },
        { duration: '30s', target: 50 },
      ],
      preAllocatedVUs: 20,
      maxVUs: 200,
    }
  },
  thresholds: {
    http_req_duration: ['p(95)<100'], // 95% of requests must complete below 100ms
    http_req_failed: ['rate<0.01'],    // Error rate must be below 1%
    retrieval_latency_ms: ['p(95)<50'], // 95% of retrievals under 50ms
    query_success_rate: ['rate>0.99'], // 99% success rate
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_KEY = __ENV.API_KEY || 'changeme';

// Diverse test queries to simulate realistic usage
const testQueries = [
  'What vector stores are supported?',
  'How do I authenticate with the API?',
  'What security practices does the company require?',
  'What is the vacation policy?',
  'How does hybrid retrieval work?',
  'What are the supported file formats?',
  'Can I use multiple vector stores?',
  'What is the rate limit for API calls?',
  'How do I report security incidents?',
  'What is the MFA requirement?'
];

export default function () {
  const headers = {
    'x-api-key': API_KEY,
    'Content-Type': 'application/json',
  };

  // Randomly select a query to simulate real usage patterns
  const randomQuery = testQueries[Math.floor(Math.random() * testQueries.length)];
  
  // Test query endpoint with realistic workload
  const queryPayload = JSON.stringify({
    q: randomQuery,
    top_k: 12,
    fusion: 'rrf'
  });

  const queryRes = http.post(`${BASE_URL}/query`, queryPayload, { headers });
  
  const isSuccess = queryRes.status === 200;
  successRate.add(isSuccess);
  
  const queryChecks = check(queryRes, {
    'query status is 200': (r) => r.status === 200,
    'query response time < 1000ms': (r) => r.timings.duration < 1000,
    'query has answer': (r) => r.json('answer') && r.json('answer').length > 0,
    'query has citations': (r) => r.json('citations') && Array.isArray(r.json('citations')),
    'retrieval debug info present': (r) => r.json('retrieval_debug') !== null,
  });

  if (isSuccess && queryRes.json('retrieval_debug')) {
    const retrievalTime = queryRes.json('retrieval_debug.retrieval_time_ms');
    if (retrievalTime) {
      retrievalLatency.add(retrievalTime);
    }
  }

  // Test streaming endpoint occasionally (10% of requests)
  if (Math.random() < 0.1) {
    const streamRes = http.get(
      `${BASE_URL}/chat/stream?q=${encodeURIComponent(randomQuery)}`,
      { headers: { 'x-api-key': API_KEY } }
    );
    
    check(streamRes, {
      'stream status is 200': (r) => r.status === 200,
      'stream response time < 2000ms': (r) => r.timings.duration < 2000,
    });
  }

  // Test health endpoint occasionally (5% of requests)
  if (Math.random() < 0.05) {
    const healthRes = http.get(`${BASE_URL}/healthz`);
    check(healthRes, {
      'health status is 200': (r) => r.status === 200,
      'health response time < 50ms': (r) => r.timings.duration < 50,
    });
  }
} 