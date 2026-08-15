// FREE deployment: Cloudflare Workers (100K requests/day free)
// Lightweight proxy that forwards to AWS Lambda or runs lightweight checks

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;

    if (path === "/health") {
      return Response.json({ status: "online", agent: "gpt-doug", version: "1.0" });
    }

    if (path === "/sentinel") {
      // Run lightweight check (no Python on CF Workers)
      return Response.json({
        agent: "zyra-sentinel",
        status: "active",
        message: "For full scan, deploy with AWS Lambda or GitHub Actions",
        free_tier: "100K requests/day"
      });
    }

    return Response.json({ error: "not found", path }, { status: 404 });
  }
};
