// Files the game server's error reports as GitHub issues.
//
// The game VM is IPv6-only and api.github.com is IPv4-only, so the VM posts
// each report here instead. Only this Worker holds the GitHub token, and only
// it picks the labels: a report can never add `auto-fix`, which starts a
// Claude fix run.

const LABELS = ["bug"];
const MAX_TITLE_LENGTH = 256;
// GitHub rejects issue bodies over 65,536 characters.
const MAX_BODY_LENGTH = 65_000;

const encoder = new TextEncoder();

async function hasRelayToken(request, relayToken) {
  if (!relayToken) {
    return false;
  }
  // Compare equal-length digests so a wrong token fails in constant time.
  const [given, expected] = await Promise.all([
    crypto.subtle.digest(
      "SHA-256",
      encoder.encode(request.headers.get("Authorization") ?? ""),
    ),
    crypto.subtle.digest("SHA-256", encoder.encode(`Bearer ${relayToken}`)),
  ]);
  const a = new Uint8Array(given);
  const b = new Uint8Array(expected);
  let diff = 0;
  for (let i = 0; i < a.length; i++) {
    diff |= a[i] ^ b[i];
  }
  return diff === 0;
}

async function readReport(request) {
  let report;
  try {
    report = await request.json();
  } catch {
    return null;
  }
  const { title, body } = report ?? {};
  if (typeof title !== "string" || !title.trim() || typeof body !== "string") {
    return null;
  }
  return {
    title: title.slice(0, MAX_TITLE_LENGTH),
    body: body.slice(0, MAX_BODY_LENGTH),
  };
}

export default {
  async fetch(request, env) {
    if (request.method !== "POST") {
      return new Response("Method not allowed\n", {
        status: 405,
        headers: { Allow: "POST" },
      });
    }
    if (!(await hasRelayToken(request, env.RELAY_TOKEN))) {
      return new Response("Unauthorized\n", { status: 401 });
    }
    const report = await readReport(request);
    if (!report) {
      return new Response('Expected JSON {"title": string, "body": string}\n', {
        status: 400,
      });
    }

    const github = await fetch(
      `https://api.github.com/repos/${env.GITHUB_REPO}/issues`,
      {
        method: "POST",
        headers: {
          Accept: "application/vnd.github+json",
          Authorization: `Bearer ${env.GITHUB_TOKEN}`,
          "Content-Type": "application/json",
          "User-Agent": "forgotten-realms-bug-relay",
          "X-GitHub-Api-Version": "2022-11-28",
        },
        body: JSON.stringify({ ...report, labels: LABELS }),
      },
    );
    if (!github.ok) {
      console.error(`GitHub returned ${github.status}: ${await github.text()}`);
      return new Response(`GitHub returned ${github.status}\n`, { status: 502 });
    }
    const issue = await github.json();
    return Response.json(
      { number: issue.number, url: issue.html_url },
      { status: 201 },
    );
  },
};
