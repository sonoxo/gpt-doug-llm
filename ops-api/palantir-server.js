const http = require("http");
const { status } = require("./palantir-readonly");

const PORT = Number(process.env.PORT || 10000);

function send(res, code, payload) {
  res.writeHead(code, {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
    "Access-Control-Allow-Origin": "*",
    "X-Content-Type-Options": "nosniff"
  });
  res.end(JSON.stringify(payload, null, 2));
}

http.createServer(async (req, res) => {
  const url = new URL(req.url, "http://localhost");

  if (req.method === "GET" && url.pathname === "/health") {
    return send(res, 200, {
      ok: true,
      service: "xunia-palantir-bridge",
      mode: "READ_ONLY",
      time: new Date().toISOString()
    });
  }

  if (req.method === "GET" && (url.pathname === "/" || url.pathname === "/api/status")) {
    return send(res, 200, await status());
  }

  return send(res, 404, { error: "not_found" });
}).listen(PORT, "0.0.0.0", () => {
  console.log("XUNIA Palantir bridge listening on 0.0.0.0:" + PORT);
});
