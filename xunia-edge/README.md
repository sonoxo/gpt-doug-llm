# XUNIA free-cloud geo guard

Cloudflare Workers Free edge filter for xunia.org and www.xunia.org. The
existing site stays on GitHub Pages. **This code is not active on xunia.org**
until the domain is routed through Cloudflare and the Worker Routes are deployed.

## Protection contract

- Cloudflare's trusted request.cf.country value equal to CN returns HTTP 403
  without an origin fetch. Client-supplied CF-IPCountry is deliberately ignored.
- All other regions and unknown countries are passed through unchanged to the
  existing origin. Region blocking is based on apparent network location, not
  nationality; VPNs can bypass it.
- A *.workers.dev preview returns a diagnostic payload with
  domainProtected:false, not the live site; any other host returns HTTP 421.
- The Worker runtime has no secrets, subscriptions, databases, or paid APIs.

## Test offline

~~~sh
node --test xunia-edge/worker.test.mjs
python3 -c 'import tomllib; [tomllib.load(open(p,"rb")) for p in ("xunia-edge/wrangler.toml","xunia-edge/wrangler.preview.toml")]'
~~~

## Optional free temporary preview

Run locally with outbound network access:

~~~sh
npx --yes wrangler@4.102.0 deploy --config xunia-edge/wrangler.preview.toml --temporary
~~~

Cloudflare issues a preview URL and a **private claim link**. Never expose the
claim link in public CI logs, issues, or chat. This does not protect xunia.org.

## Production setup (needs access to the domain and Cloudflare account)

1. Add xunia.org to a Cloudflare **Free** zone. Preserve existing GitHub Pages
   A records, the www CNAME, and all existing mail/TXT/MX records. Keep
   the GitHub Pages custom-domain setting (docs/CNAME) unchanged.
2. At the registrar, set the nameservers provided by Cloudflare. Verify
   working HTTPS and GitHub Pages availability after propagation.
3. Set the Cloudflare DNS records for both xunia.org and www.xunia.org to
   Proxied (orange cloud), keeping GitHub Pages as the origin.
4. Authenticate Wrangler in the owner's environment and deploy:

~~~sh
npx --yes wrangler@4.102.0 deploy --config xunia-edge/wrangler.toml
~~~

Alternatively, add CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN as protected
GitHub Actions secrets, merge the reviewed branch, and explicitly run
the "XUNIA Free Edge Guard" workflow_dispatch from main. Scope tokens tightly
to the Cloudflare Worker and xunia.org zone. Never put tokens in git or chat.

5. Verify working origin paths and an allowed-country request. Test denial
   from a real CN egress and confirm HTTP 403 in Cloudflare security analytics.
   A fake country header is NOT an adequate live verification.
6. Rollback: remove the Worker Routes or disable the Worker in Cloudflare,
   leaving DNS and the GitHub Pages origin otherwise untouched.

The Cloudflare Workers Free request limit is 100,000/day as of 2026-10-22.
Do not silently upgrade to a paid tier or treat CI tests as proof of live
geographical enforcement.
