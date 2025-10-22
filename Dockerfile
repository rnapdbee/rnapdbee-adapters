FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONPATH=/rnapdbee-adapters/src

RUN apt-get update -y \
 && apt-get install -y \
       build-essential \
       ca-certificates \
       curl \
       git \
       gnupg \
       pdf2svg \
       python3 \
       python3-pip \
 && rm -rf /var/lib/apt/lists/*

# Install Mono
RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 3FA7E0328081BFF6A14DA29AA6A19B38D3D831EF \
 && echo "deb https://download.mono-project.com/repo/ubuntu stable-focal main" | tee /etc/apt/sources.list.d/mono-official-stable.list \
 && apt-get update -y \
 && apt-get install -y \
       mono-devel \
 && rm -rf /var/lib/apt/lists/*

# Install ViennaRNA (RNAplot for RNApuzzler)
# ADD https://www.tbi.univie.ac.at/RNA/download/ubuntu/ubuntu_24_04/viennarna_2.7.0-1_amd64.deb /tmp/viennarna.deb
# RUN dpkg -i /tmp/viennarna.deb

# Install HiGHS
# ADD https://github.com/JuliaBinaryWrappers/HiGHSstatic_jll.jl/releases/download/HiGHSstatic-v1.11.0%2B1/HiGHSstatic.v1.11.0.x86_64-linux-gnu-cxx11.tar.gz /usr/local
ADD app/HiGHSstatic.v1.11.0.x86_64-linux-gnu-cxx11.tar.gz /usr/local

# Install svgcleaner
# ADD https://github.com/RazrFalcon/svgcleaner/releases/download/v0.9.5/svgcleaner_linux_x86_64_0.9.5.tar.gz /usr/local/bin
ADD app/svgcleaner_linux_x86_64_0.9.5.tar.gz /usr/local/bin

# Install IronPython
# ADD https://github.com/IronLanguages/ironpython3/releases/download/v3.4.2/ironpython_3.4.2.deb /tmp/ironpython_3.4.2.deb
COPY app/ironpython_3.4.2.deb /tmp/ironpython_3.4.2.deb
RUN dpkg -i /tmp/ironpython_3.4.2.deb

# PseudoViewer and RNApuzzler wrappers
COPY app/pseudoviewer/ /pseudoviewer/
COPY app/rnapuzzler/ /RNAplot/
ENV PATH=/pseudoviewer:/RNAplot:${PATH}

EXPOSE 80

COPY docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]

COPY requirements.txt /tmp/requirements.txt
RUN pip install --break-system-packages --no-cache-dir --ignore-installed -r /tmp/requirements.txt

COPY src/adapters /rnapdbee-adapters/src/adapters

ENV ADAPTERS_GUNICORN_LOG_LEVEL=INFO \
    ADAPTERS_MAX_REQUESTS=10 \
    ADAPTERS_PSEUDOVIEWER_TIMEOUT=60 \
    ADAPTERS_THREADS=1 \
    ADAPTERS_WORKERS=6 \
    ADAPTERS_WORKER_TIMEOUT=1200 \
    CLI2REST_BARNABA_URL=http://localhost:8000 \
    CLI2REST_BPNET_URL=http://localhost:8000 \
    CLI2REST_FR3D_URL=http://localhost:8000 \
    CLI2REST_MAXIT_URL=http://localhost:8000 \
    CLI2REST_MCANNOTATE_URL=http://localhost:8000 \
    CLI2REST_RCHIE_URL=http://localhost:8000 \
    CLI2REST_RNAVIEW_URL=http://localhost:8000
