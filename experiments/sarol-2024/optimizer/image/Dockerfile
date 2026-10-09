# paper-trail's optimizer image: the engine's isolation image (agentic-label-opt
# isolation/Dockerfile, same base pinned by its multi-platform index digest, same Claude Code
# install) plus python3, so the optimizer can run the program's own Python checks (Phil 2026-09-22:
# paper-trail's optimizer image has Python; the engine's has none). The graders keep the image
# without Python, so their reach does not grow.
#
# Build (the tag must name the Claude Code version inside, S2's image form):
#   docker build --build-arg CLAUDE_CODE_VERSION=2.1.295 -t paper-trail-optimizer:2.1.295 \
#     -f experiments/sarol-2024/optimizer/image/Dockerfile experiments/sarol-2024/optimizer/image
# or: python3 experiments/sarol-2024/optimizer/sarol_optimizer.py --build
FROM node:22-bookworm-slim@sha256:43ac6c60b8f89723f746e8a92ce91abd5017e627ce1ddfe4238355d3a30b772c
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        curl \
        ca-certificates \
        python3 \
    && rm -rf /var/lib/apt/lists/*
ARG CLAUDE_CODE_VERSION=2.1.295
RUN npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}
WORKDIR /workspace/program
RUN chown 1000:1000 /workspace/program
USER 1000:1000
