import assert from "node:assert/strict";
import { afterEach, beforeEach, describe, it, mock } from "node:test";

import relay from "../src/index.js";

const env = {
  GITHUB_REPO: "owner/repo",
  GITHUB_TOKEN: "github-token",
  RELAY_TOKEN: "relay-token",
};

function postReport(report, authorization = `Bearer ${env.RELAY_TOKEN}`) {
  return new Request("https://relay.example/", {
    method: "POST",
    headers: { Authorization: authorization },
    body: typeof report === "string" ? report : JSON.stringify(report),
  });
}

describe("bug relay", () => {
  let githubFetch;

  beforeEach(() => {
    githubFetch = mock.method(globalThis, "fetch", async () =>
      Response.json(
        { number: 7, html_url: "https://github.com/owner/repo/issues/7" },
        { status: 201 },
      ),
    );
  });

  afterEach(() => {
    mock.restoreAll();
  });

  it("files a report as an issue labeled only bug", async () => {
    const response = await relay.fetch(
      postReport({ title: "Crash", body: "trace", labels: ["auto-fix"] }),
      env,
    );

    assert.equal(response.status, 201);
    assert.deepEqual(await response.json(), {
      number: 7,
      url: "https://github.com/owner/repo/issues/7",
    });
    const [url, init] = githubFetch.mock.calls[0].arguments;
    assert.equal(url, "https://api.github.com/repos/owner/repo/issues");
    assert.equal(init.headers.Authorization, "Bearer github-token");
    assert.deepEqual(JSON.parse(init.body), {
      title: "Crash",
      body: "trace",
      labels: ["bug"],
    });
  });

  it("truncates titles and bodies to GitHub's limits", async () => {
    await relay.fetch(
      postReport({ title: "t".repeat(300), body: "b".repeat(70_000) }),
      env,
    );

    const sent = JSON.parse(githubFetch.mock.calls[0].arguments[1].body);
    assert.equal(sent.title.length, 256);
    assert.equal(sent.body.length, 65_000);
  });

  it("rejects a wrong relay token without calling GitHub", async () => {
    const response = await relay.fetch(
      postReport({ title: "Crash", body: "trace" }, "Bearer wrong"),
      env,
    );

    assert.equal(response.status, 401);
    assert.equal(githubFetch.mock.callCount(), 0);
  });

  it("rejects every request when no relay token is configured", async () => {
    const response = await relay.fetch(
      postReport({ title: "Crash", body: "trace" }, "Bearer undefined"),
      { ...env, RELAY_TOKEN: undefined },
    );

    assert.equal(response.status, 401);
    assert.equal(githubFetch.mock.callCount(), 0);
  });

  it("rejects reports that are not JSON or lack a title or body", async () => {
    const malformed = [
      "not json",
      { body: "trace" },
      { title: "  ", body: "trace" },
      { title: "Crash" },
    ];

    for (const report of malformed) {
      const response = await relay.fetch(postReport(report), env);
      assert.equal(response.status, 400);
    }
    assert.equal(githubFetch.mock.callCount(), 0);
  });

  it("only accepts POST", async () => {
    const response = await relay.fetch(
      new Request("https://relay.example/"),
      env,
    );

    assert.equal(response.status, 405);
    assert.equal(githubFetch.mock.callCount(), 0);
  });

  it("returns 502 when GitHub rejects the issue", async () => {
    githubFetch.mock.mockImplementation(
      async () => new Response("Bad credentials", { status: 401 }),
    );
    const logged = mock.method(console, "error", () => {});

    const response = await relay.fetch(
      postReport({ title: "Crash", body: "trace" }),
      env,
    );

    assert.equal(response.status, 502);
    assert.match(logged.mock.calls[0].arguments[0], /401: Bad credentials/);
  });
});
