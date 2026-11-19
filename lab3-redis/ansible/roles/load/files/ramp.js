// overload profile: the ramp crosses both tier limits on purpose, so 429 is expected here
import http from 'k6/http';
import { check } from 'k6';

http.setResponseCallback(http.expectedStatuses(200, 429));

export const options = {
  scenarios: {
    free_tier: {
      executor: 'ramping-vus',
      exec: 'hit',
      env: { KEY: 'loadtest-free-1' },
      stages: [
        { duration: '30s', target: 40 },
        { duration: '60s', target: 40 },
        { duration: '10s', target: 0 },
      ],
    },
    pro_tier: {
      executor: 'ramping-vus',
      exec: 'hit',
      startTime: '10s',
      env: { KEY: 'loadtest-pro-1' },
      stages: [
        { duration: '40s', target: 300 },
        { duration: '50s', target: 300 },
        { duration: '10s', target: 0 },
      ],
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<250'],
    checks: ['rate>0.5'],
  },
};

export function hit() {
  const res = http.get(
    'http://127.0.0.1:8080/rates',
    { headers: { 'X-API-KEY': __ENV.KEY } }
  );
  check(res, {
    '200 or 429': (r) => r.status === 200 || r.status === 429,
    'Retry-After on 429': (r) => r.status !== 429 || r.headers['Retry-After'] !== undefined,
  });
}
