# Bug relay

A Cloudflare Worker that files the game server's error reports as GitHub
issues. The game VM is IPv6-only and `api.github.com` is IPv4-only, so
`backend/services/error_reporter.py` posts each report here instead.

The GitHub token lives only in this Worker. The VM holds a relay token that
can do nothing except file a report. Issues get the `bug` label only: add
`auto-fix` (or comment `@claude`) to start the fix workflow.

## Settings

| Name | Where | Value |
| --- | --- | --- |
| `GITHUB_TOKEN` | Worker secret | Fine-grained token for this repository only, with Issues: read and write |
| `RELAY_TOKEN` | Worker secret | A random string |
| `ERROR_RELAY_URL` | `backend/.env` on the VM | This Worker's URL |
| `ERROR_RELAY_TOKEN` | `backend/.env` on the VM | The same value as `RELAY_TOKEN` |

## Commands

Run these from this directory.

```bash
node --test                              # unit tests, no install needed
npx wrangler@4 deploy                    # publish the Worker
npx wrangler@4 secret put GITHUB_TOKEN   # replace the GitHub token (prompts for it)
npx wrangler@4 tail                      # watch live requests and errors
```
