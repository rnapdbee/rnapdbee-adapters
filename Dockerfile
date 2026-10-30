ARG PYTHON_VERSION=3.14
# Must satisfy tool.uv.required-version in pyproject.toml.
ARG UV_VERSION=0.13.6

# Single source of the uv binaries, pulled once and reused by both stages.
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM python:${PYTHON_VERSION}-bookworm AS builder

RUN apt-get update \
 && apt-get install --no-install-recommends -y \
      bison \
      cmake \
      flex \
 && rm -rf /var/lib/apt/lists/*

COPY --from=uv /uv /uvx /bin/

WORKDIR /build

# Copy only the files needed to resolve the environment so the expensive
# dependency install is cached independently of the application sources.
COPY pyproject.toml uv.lock ./

# Keep the virtualenv at /opt/venv so the runtime stage, PATH and VIRTUAL_ENV
# stay unchanged.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv

RUN uv sync --frozen --no-dev --no-install-project --python /usr/local/bin/python

#######################################

FROM python:${PYTHON_VERSION}-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/rnapdbee-adapters/src \
    UV_PROJECT_ENVIRONMENT=/opt/venv

# uv is needed by manage.sh to install the test group into the running
# container; the runtime venv itself is populated from the builder stage.
COPY --from=uv /uv /uvx /bin/

RUN apt-get update -y \
 && apt-get install -y \
       ca-certificates \
       dirmngr \
       gnupg \
 && rm -rf /var/lib/apt/lists/*

# Install Mono
RUN gpg --homedir /tmp --no-default-keyring --keyring gnupg-ring:/usr/share/keyrings/mono-official-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 3FA7E0328081BFF6A14DA29AA6A19B38D3D831EF \
 && chmod +r /usr/share/keyrings/mono-official-archive-keyring.gpg \
 && echo "deb [signed-by=/usr/share/keyrings/mono-official-archive-keyring.gpg] https://download.mono-project.com/repo/debian stable-buster main" | tee /etc/apt/sources.list.d/mono-official-stable.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends \
      mono-devel \
 && rm -rf /var/lib/apt/lists/*

# Install HiGHS (https://github.com/JuliaBinaryWrappers/HiGHSstatic_jll.jl/releases/download/HiGHSstatic-v1.11.0%2B1/HiGHSstatic.v1.11.0.x86_64-linux-gnu-cxx11.tar.gz)
ADD app/HiGHSstatic.v1.11.0.x86_64-linux-gnu-cxx11.tar.gz /usr/local

# Install svgcleaner (https://github.com/RazrFalcon/svgcleaner/releases/download/v0.9.5/svgcleaner_linux_x86_64_0.9.5.tar.gz)
ADD app/svgcleaner_linux_x86_64_0.9.5.tar.gz /usr/local/bin

# Install IronPython (https://github.com/IronLanguages/ironpython3/releases/download/v3.4.2/ironpython_3.4.2.deb)
COPY app/ironpython_3.4.2.deb /tmp/ironpython_3.4.2.deb
RUN dpkg -i /tmp/ironpython_3.4.2.deb

# PseudoViewer wrapper
COPY app/pseudoviewer/ /pseudoviewer/

ENV PATH="/opt/venv/bin:/pseudoviewer:${PATH}" \
    VIRTUAL_ENV="/opt/venv" \
    ADAPTERS_GUNICORN_LOG_LEVEL=INFO \
    ADAPTERS_MAX_REQUESTS=10 \
    ADAPTERS_PSEUDOVIEWER_TIMEOUT=60 \
    ADAPTERS_RNAPUZZLER_LOG_JSON=false \
    ADAPTERS_THREADS=1 \
    ADAPTERS_WORKERS=4 \
    ADAPTERS_WORKER_TIMEOUT=1200 \
    CLI2REST_BARNABA_URL=http://localhost:8000 \
    CLI2REST_BPNET_URL=http://localhost:8000 \
    CLI2REST_FR3D_URL=http://localhost:8000 \
    CLI2REST_MAXIT_URL=http://localhost:8000 \
    CLI2REST_MCANNOTATE_URL=http://localhost:8000 \
    CLI2REST_RCHIE_URL=http://localhost:8000 \
    CLI2REST_RNAVIEW_URL=http://localhost:8000 \
    CLI2REST_RNAPUZZLER_URL=http://localhost:8000

EXPOSE 80

COPY docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]

COPY --from=builder /opt/venv /opt/venv

COPY src/adapters /rnapdbee-adapters/src/adapters
