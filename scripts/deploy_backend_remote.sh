#!/usr/bin/env bash

set -Eeuo pipefail

readonly BUNDLE_PATH="${1:?usage: deploy_backend_remote.sh BUNDLE_PATH EXPECTED_SHA}"
readonly EXPECTED_SHA="${2:?usage: deploy_backend_remote.sh BUNDLE_PATH EXPECTED_SHA}"
readonly REPO_ROOT="${DEPLOY_REPO_ROOT:-/home/andreas/forgotten-realms}"
readonly SERVICE_NAME="${DEPLOY_SERVICE_NAME:-socket-server}"
readonly DEPLOY_REF="refs/remotes/github-actions/main"

requirements_file=""

cleanup() {
    rm -f -- "${BUNDLE_PATH}"
    if [[ "${BASH_SOURCE[0]}" == "/tmp/deploy-backend-${EXPECTED_SHA}.sh" ]]; then
        rm -f -- "${BASH_SOURCE[0]}"
    fi
    if [[ -n "${requirements_file}" ]]; then
        rm -f -- "${requirements_file}"
    fi
}
trap cleanup EXIT

if [[ ! "${EXPECTED_SHA}" =~ ^[0-9a-f]{40}$ ]]; then
    echo "Expected a full lowercase Git commit SHA, got: ${EXPECTED_SHA}" >&2
    exit 2
fi

if [[ ! -f "${BUNDLE_PATH}" ]]; then
    echo "Deployment bundle not found: ${BUNDLE_PATH}" >&2
    exit 2
fi

if ! git -C "${REPO_ROOT}" rev-parse --git-dir >/dev/null 2>&1; then
    echo "Deployment checkout not found: ${REPO_ROOT}" >&2
    exit 2
fi

cd "${REPO_ROOT}"

if [[ "$(git symbolic-ref --quiet --short HEAD || true)" != "main" ]]; then
    echo "Refusing to deploy because ${REPO_ROOT} is not on branch main." >&2
    exit 1
fi

if ! git diff-index --quiet HEAD --; then
    echo "Refusing to deploy over tracked changes in ${REPO_ROOT}." >&2
    echo "Ignored and untracked runtime files are intentionally allowed." >&2
    exit 1
fi

git bundle verify "${BUNDLE_PATH}"
git fetch --no-tags "${BUNDLE_PATH}" "HEAD:${DEPLOY_REF}"

BUNDLED_SHA="$(git rev-parse "${DEPLOY_REF}^{commit}")"
readonly BUNDLED_SHA
if [[ "${BUNDLED_SHA}" != "${EXPECTED_SHA}" ]]; then
    echo "Bundle commit ${BUNDLED_SHA} does not match ${EXPECTED_SHA}." >&2
    exit 1
fi

PREVIOUS_SHA="$(git rev-parse HEAD)"
readonly PREVIOUS_SHA
if ! git merge-base --is-ancestor "${PREVIOUS_SHA}" "${BUNDLED_SHA}"; then
    echo "Refusing a non-fast-forward deployment (${PREVIOUS_SHA} -> ${BUNDLED_SHA})." >&2
    exit 1
fi

# Install only when dependencies changed, while the old process is still up.
# The existing virtualenv and all ignored runtime state stay in place.
if ! git diff --quiet "${PREVIOUS_SHA}" "${BUNDLED_SHA}" -- backend/requirements.txt; then
    requirements_file="$(mktemp)"
    git show "${BUNDLED_SHA}:backend/requirements.txt" >"${requirements_file}"
    "${REPO_ROOT}/backend/venv/bin/python" -m pip install -r "${requirements_file}"
fi

# Check again in case a tracked file changed while dependencies were installing.
if ! git diff-index --quiet HEAD --; then
    echo "Tracked files changed during deployment; leaving the running version untouched." >&2
    exit 1
fi

git merge --ff-only "${BUNDLED_SHA}"

if sudo systemctl restart "${SERVICE_NAME}" && sleep 2 && sudo systemctl is-active --quiet "${SERVICE_NAME}"; then
    echo "Deployed ${BUNDLED_SHA}; ${SERVICE_NAME} is active."
    exit 0
fi

echo "The new service failed to start; rolling tracked source back to ${PREVIOUS_SHA}." >&2
sudo systemctl stop "${SERVICE_NAME}" || true

# Do not overwrite an operator or admin publish that raced with the health
# check. A failed deployment is preferable to destroying a newer tracked edit.
if [[ "$(git rev-parse HEAD)" != "${BUNDLED_SHA}" ]] || ! git diff-index --quiet HEAD --; then
    echo "Tracked source changed after deployment; refusing automatic rollback." >&2
    exit 1
fi

git reset --hard "${PREVIOUS_SHA}"
sudo systemctl restart "${SERVICE_NAME}"
echo "Rollback completed, but deployment ${BUNDLED_SHA} failed." >&2
exit 1
