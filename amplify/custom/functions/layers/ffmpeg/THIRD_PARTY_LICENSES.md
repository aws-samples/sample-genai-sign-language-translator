# Third-Party License Notice — FFmpeg (GPL v3)

This Lambda layer bundles a statically-linked **FFmpeg** binary (`bin/ffmpeg`).

| Property | Value |
|----------|-------|
| Component | FFmpeg (static build) |
| Target platform | Linux x86-64 (ELF, statically linked) |
| License | **GNU General Public License v3.0 or later (GPL-3.0-or-later)** |
| Bundled SHA-256 | `82802037afaf2f2f0b0d55077594e94d4117e80307fdc0786d2919ed5e881a36` |

The build links several GPL-licensed FFmpeg sub-libraries, including
`libavcodec`, `libavformat`, `libavfilter`, `libswscale`, `libswresample`,
`libpostproc`, `libavutil`, and `libavdevice`, each carrying
"GPL version 3 or later".

## License Attribution

FFmpeg is free software licensed under the GNU General Public License
version 3. The full license text is available at:

- https://www.gnu.org/licenses/gpl-3.0.html
- https://www.ffmpeg.org/legal.html

## Source Code Availability (GPL-3 §3 obligation)

GPL-3 requires that the corresponding source code be made available to anyone
who receives the binary. The complete corresponding source for this FFmpeg
build is available from the upstream project:

- FFmpeg source: https://www.ffmpeg.org/download.html
- Static build provenance: https://johnvansickle.com/ffmpeg/

If you redistribute this repository (or any artifact containing this binary),
you **must** accompany it with, or provide a written offer to supply, the
corresponding FFmpeg source code under the terms of GPL-3.

## Usage Context & Compliance

This repository is published as an **AWS sample / demonstration** that is
cloned and self-deployed by each user into their own AWS account. FFmpeg is
invoked as a separate executable (via subprocess), not linked into the
application source, so the project's own code is not a derivative work of
FFmpeg. The application code remains under its own license (see repository
`LICENSE`); the bundled FFmpeg binary remains under GPL-3 and is governed by
this notice.

### If you intend to distribute this as a packaged product

The GPL-3 source-availability and copyleft obligations are triggered by
distribution. For a packaged/commercial product, prefer one of:

1. Pulling FFmpeg at build/deploy time instead of bundling it (see
   `download_ffmpeg.sh` in this directory), and shipping this notice; or
2. Replacing the GPL build with an **LGPL-licensed** FFmpeg build (configure
   with `--disable-gpl` and without `--enable-nonfree`), or an MIT/BSD-licensed
   alternative, to avoid copyleft obligations on bundled artifacts.

Reference: https://w.amazon.com/bin/view/Open_Source/Tools/Repolinter/Ruleset/Prohibited-License/
