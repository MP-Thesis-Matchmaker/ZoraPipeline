FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies in their own layer so `docker build` only re-runs pip
# when requirements.txt actually changes, not on every source edit.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
COPY schema/ ./schema/
COPY scripts/ ./scripts/

# data/ is expected to be bind-mounted at runtime (it's where
# zora_publications.jsonl and state.json live, and where the container writes
# its output back onto the host / repo checkout). This placeholder just means
# the image doesn't error out if someone runs it without a mount for a quick
# smoke test.
RUN mkdir -p data/raw

# No USER directive here on purpose: this image is only ever run as a
# short-lived batch job (`docker run --rm ...`), never as a long-lived
# service, so the meaningful security boundary is the container sandbox
# itself, not the in-container UID. What DOES matter is that files written
# to the bind-mounted data/ directory come out owned by the invoking host
# user rather than root — that's handled at `docker run` time with
# `--user "$(id -u):$(id -g)"` (see .github/workflows and README), which
# also makes local runs on any dev machine behave identically without sudo
# cleanup. Baking a fixed UID into the image would only work by coincidence
# on whichever host happens to share it.

ENTRYPOINT ["python", "-m", "src.harvest"]
CMD ["--mode", "incremental"]
