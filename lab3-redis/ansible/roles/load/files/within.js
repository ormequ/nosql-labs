// in-budget profile: constant arrival rates below both limits, so every request must get 200
import http from 'k6/http';
import { check } from 'k6';

export const options = {
  scenarios: {
    free_tier: {
      executor: 'constant-arrival-rate',
      rate: 55, timeUnit: '1m',
      duration: '2m',
      preAllocatedVUs: 5, maxVUs: 10,
      exec: 'hit',
      env: { KEY: 'budget-free-1' },
    },
    pro_tier: {
      executor: 'constant-arrival-rate',
      rate: 540, timeUnit: '1m',
      duration: '2m',
      preAllocatedVUs: 20, maxVUs: 40,
      exec: 'hit',
      env: { KEY: 'budget-pro-1' },
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<250'],
    checks: ['rate==1'],
  },
};

export function hit() {
  const res = http.get(
    'http://127.0.0.1:8080/rates',
    { headers: { 'X-API-KEY': __ENV.KEY } }
  );
  check(res, {
    '200': (r) => r.status === 200,
  });
}
