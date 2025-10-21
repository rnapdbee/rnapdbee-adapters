FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONPATH=/rnapdbee-adapters/src \
    ADAPTERS_WORKERS=3 \
    ADAPTERS_THREADS=1 \
    ADAPTERS_GUNICORN_LOG_LEVEL=info \
    ADAPTERS_WORKER_TIMEOUT=1200 \
    ADAPTERS_MAX_REQUESTS=10

RUN apt-get update -y \
 && apt-get install -y \
       build-essential \
       ca-certificates \
       curl \
       ghostscript \
       git \
       gnupg \
       inkscape \
       pdf2svg \
       python2.7 \
       python2.7-dev \
       python3 \
       python3-venv \
       r-base \
 && apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 3FA7E0328081BFF6A14DA29AA6A19B38D3D831EF \
 && echo "deb https://download.mono-project.com/repo/ubuntu stable-focal main" | tee /etc/apt/sources.list.d/mono-official-stable.list \
 && apt-get update && apt-get install -y mono-devel \
 && rm -rf /var/lib/apt/lists/*

# Install HiGHS
ADD app/highs/HiGHSstatic.v1.8.1.x86_64-linux-gnu-cxx11.tar.gz /usr/local

# Install svgcleaner
ADD https://github.com/RazrFalcon/svgcleaner/releases/download/v0.9.5/svgcleaner_linux_x86_64_0.9.5.tar.gz /usr/local/bin

# RNApuzzler copy
COPY app/rnapuzzler /RNAplot

# PseudoViewer copy
COPY app/pseudoviewer/ pseudoviewer/

EXPOSE 80

COPY docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]

COPY src/adapters /rnapdbee-adapters/src/adapters
