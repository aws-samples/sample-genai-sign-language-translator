#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${SCRIPT_DIR}/bin"
FFMPEG_BIN="${BIN_DIR}/ffmpeg"

FFMPEG_VERSION="7.0.2"
FFMPEG_URL="https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
FFMPEG_SHA256="abda8d77ce8309141f83ab8edf0596834087c52467f6badf376a6a2a4c87cf67"

if [ -f "${FFMPEG_BIN}" ]; then
    echo "ffmpeg binary already exists at ${FFMPEG_BIN}, skipping download."
    exit 0
fi

echo "Downloading ffmpeg ${FFMPEG_VERSION} static build..."
mkdir -p "${BIN_DIR}"

TMPDIR=$(mktemp -d)
trap 'rm -rf "${TMPDIR}"' EXIT

curl -fSL "${FFMPEG_URL}" -o "${TMPDIR}/ffmpeg.tar.xz"

echo "Verifying checksum..."
echo "${FFMPEG_SHA256}  ${TMPDIR}/ffmpeg.tar.xz" | sha256sum -c - 2>/dev/null || \
    shasum -a 256 -c <(echo "${FFMPEG_SHA256}  ${TMPDIR}/ffmpeg.tar.xz")

echo "Extracting ffmpeg binary..."
tar -xJf "${TMPDIR}/ffmpeg.tar.xz" -C "${TMPDIR}"
cp "${TMPDIR}/ffmpeg-${FFMPEG_VERSION}-amd64-static/ffmpeg" "${FFMPEG_BIN}" 2>/dev/null || \
    cp "$(find "${TMPDIR}" -name ffmpeg -type f | head -1)" "${FFMPEG_BIN}"
chmod +x "${FFMPEG_BIN}"

echo "Done. ffmpeg installed to ${FFMPEG_BIN}"
