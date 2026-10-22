// Cloudflare Workers Free edge policy for XUNIA. Only request.cf metadata
// (not visitor-supplied headers) is authoritative for the source country.
const PRODUCTION_HOSTS = new Set(['xunia.org', 'www.xunia.org']);

function denied() {
  return new Response('Access restricted by regional access policy.\n', {
    status: 403,
    headers: {
      'content-type': 'text/plain; charset=utf-8',
      'cache-control': 'no-store',
      'x-content-type-options': 'nosniff',
      'x-robots-tag': 'noindex',
    },
  });
}

export async function handleRequest(request, originFetch = fetch) {
  const country = request.cf?.country;
  if (typeof country === 'string' && country.toUpperCase() === 'CN') {
    return denied();
  }

  const host = new URL(request.url).hostname.toLowerCase();
  if (PRODUCTION_HOSTS.has(host)) {
    // A Cloudflare Worker Route forwards unchanged to the configured origin.
    return originFetch(request);
  }

  if (host.endsWith('.workers.dev')) {
    // Preview proves the Worker runs but NOT that xunia.org is protected.
    return Response.json({
      service: 'xunia-geo-guard',
      mode: 'preview',
      domainProtected: false,
      liveDomain: 'xunia.org',
      policy: 'deny-country-CN',
    }, {headers: {'cache-control': 'no-store', 'x-robots-tag': 'noindex'}});
  }

  return new Response('Unrecognized host.\n', {
    status: 421,
    headers: {'content-type': 'text/plain; charset=utf-8', 'cache-control': 'no-store'},
  });
}

export default {
  fetch(request) {
    return handleRequest(request);
  },
};
