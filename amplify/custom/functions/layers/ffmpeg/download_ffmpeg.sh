#!/usr/bin/env bash
#
# Build-time fetch for the FFmpeg Lambda layer binary.
#
# Rationale: the FFmpeg binary is ~79 MB and is GPL-3 licensed. Pulling it at
# build time (instead of committing it to the repository) keeps the repo small
# and makes the binary's provenance explicit and verifiable via checksum.
#
# Usage:
#   ./download_ffmpeg.sh
#
# Run this before `npx ampx sandbox` / `npx ampx pipeline-deploy` if the
# binary is not already present in ./bin/ffmpeg.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${SCRIPT_DIR}/bin"
BIN_PATH="${BIN_DIR}/ffmpeg"

# Pinned, GPL-3 static build (John Van Sickle release-strict builds).
# Update FFMPEG_URL and EXPECTED_SHA256 together when bumping the version.
FFMPEG_URL="https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
EXPECTED_SHA256=""   # optional: set to enforce checksum verification

if [[ -x "${BIN_PATH}" ]]; then
  echo "ffmpeg already present at ${BIN_PATH}; skipping download."
  exit 0
fi

mkdir -p "${BIN_DIR}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

echo "Downloading FFmpeg static build from ${FFMPEG_URL} ..."
curl -fsSL "${FFMPEG_URL}" -o "${TMP_DIR}/ffmpeg.tar.xz"

if [[ -n "${EXPECTED_SHA256}" ]]; then
  echo "Verifying checksum ..."
  echo "${EXPECTED_SHA256}  ${TMP_DIR}/ffmpeg.tar.xz" | sha256sum -c -
fi

tar -xf "${TMP_DIR}/ffmpeg.tar.xz" -C "${TMP_DIR}"
EXTRACTED_BIN="$(find "${TMP_DIR}" -type f -name ffmpeg | head -n1)"

if [[ -z "${EXTRACTED_BIN}" ]]; then
  echo "ERROR: ffmpeg binary not found in downloaded archive." >&2
  exit 1
fi

cp "${EXTRACTED_BIN}" "${BIN_PATH}"
chmod +x "${BIN_PATH}"
echo "FFmpeg installed at ${BIN_PATH}"
echo "NOTE: This binary is GPL-3 licensed. See THIRD_PARTY_LICENSES.md."
