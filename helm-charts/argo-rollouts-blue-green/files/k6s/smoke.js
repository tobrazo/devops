import http from 'k6/http';
import { check, sleep } from 'k6';

// Pre-promotion smoke test run by Argo Rollouts against the preview (green) stack.
// Override the target with -e PREVIEW_URL=... ; defaults to the chart's preview host.
const TARGET = __ENV.PREVIEW_URL || 'https://tobrazo-app-preview.example.com/';

export const options = {
  vus: 5,               // 5 concurrent virtual users
  duration: '30s',      // 30s smoke run
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% of requests under 500ms
    http_req_failed: ['rate<0.01'],   // less than 1% errors
  },
};

export default function () {
  const res = http.get(TARGET);

  check(res, {
    'status is 200': (r) => r.status === 200,
  });

  sleep(1); // small pause between requests
}
