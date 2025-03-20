# syntax=docker/dockerfile:1

ARG maxit_version=11.100
ARG rchie_dir=/usr/local/lib/R/site-library/rchie

# Use latest branch, but another working alternative is this commit:
# https://github.com/BGSU-RNA/fr3d-python/commit/407c8b2f0fa2bc9682e4ab8f3108867a8892d6fd
ARG fr3d_commit=latest

################################################################################

FROM ubuntu:22.04 AS maxit-builder

ARG maxit_version
ENV DEBIAN_FRONTEND=noninteractive \
    RCSBROOT=/maxit-v${maxit_version}-prod-src

RUN apt-get update -y \
 && apt-get install -y \
        bison \
        build-essential \
        ca-certificates \
        curl \
        flex \
        tcsh \
        sed \
 && rm -rf /var/lib/apt/lists/*

RUN curl -L https://sw-tools.rcsb.org/apps/MAXIT/maxit-v${maxit_version}-prod-src.tar.gz | tar xz

COPY app/maxit app/maxit

RUN cd ${RCSBROOT} \
 && patch -p0 < /app/maxit/bison_patch \
 && make \
 && make binary

################################################################################

FROM ubuntu:22.04 AS rnaview-builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -y \
 && apt-get install -y \
        build-essential \
        curl \
 && rm -rf /var/lib/apt/lists/*

COPY app/rnaview app/rnaview

RUN tar -xf app/rnaview/RNAVIEW.tar.gz

RUN patch -p0 < app/rnaview/patch \
 && cd RNAVIEW \
 && make

################################################################################

FROM ubuntu:22.04 AS python-builder

ENV DEBIAN_FRONTEND=noninteractive \
    PATH=/venv/bin:$PATH

RUN apt-get update -y \
 && apt-get install -y \
        build-essential \
        python3 \
        python3-pip \
        python3-venv \
        git \
 && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /venv

COPY requirements.txt .

RUN pip3 install --upgrade --no-cache-dir wheel setuptools \
 && pip3 install --no-cache-dir -r requirements.txt

################################################################################

FROM ubuntu:22.04 AS r-builder

ARG rchie_dir
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -y \
 && apt-get install -y \
        curl \
        r-base \
        libcurl4-openssl-dev \
 && rm -rf /var/lib/apt/lists/*

RUN echo 'options(BioC_mirror = "https://packagemanager.rstudio.com/bioconductor", repos = c(REPO_NAME = "https://packagemanager.rstudio.com/all/__linux__/jammy/2022-11-09+MToxNDMzODE3MywyOjQ1MjYyMTU7RDFFQTQ0MUE"))' > ~/.Rprofile \
 && Rscript -e 'install.packages(c("BiocManager", "optparse", "RColorBrewer"), lib="/usr/local/lib/R/site-library")' \
 && Rscript -e 'BiocManager::install("R4RNA", lib="/usr/local/lib/R/site-library")'

COPY app/rchie/rchie.R ${rchie_dir}/rchie.R

################################################################################

FROM ubuntu:22.04 AS server

ARG maxit_version
ARG rchie_dir
ARG fr3d_commit

ENV DEBIAN_FRONTEND=noninteractive \
    NUCLEIC_ACID_DIR=/bpnet-master/sysfiles \
    PATH=${PATH}:/bpnet-master/bin:/metbp-MetBPv1.2.4/bin:/maxit/bin:/mc-annotate:/rnaview/bin:/venv/bin:${rchie_dir}:/pseudoviewer:/RNAplot:/svg-cleaner \
    PYTHONPATH=/rnapdbee-adapters/src \
    RCSBROOT=/maxit \
    RNAVIEW=/rnaview \
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

# Prepare Python 2.7 environment for FR3D
RUN curl https://bootstrap.pypa.io/pip/2.7/get-pip.py -o get-pip.py \
 && python2.7 get-pip.py \
 && python2.7 -m pip install virtualenv \
 && python2.7 -m virtualenv /py27_env

# MAXIT build
COPY --from=maxit-builder /maxit-v${maxit_version}-prod-src /maxit

# R build (with RChie build)
COPY --from=r-builder /usr/local/lib/R/site-library /usr/local/lib/R/site-library

# RNAView build
COPY --from=rnaview-builder /RNAVIEW /rnaview

# Python build
COPY --from=python-builder /venv /venv

# RNApuzzler copy
COPY app/rnapuzzler /RNAplot

# PseudoViewer copy
COPY app/pseudoviewer/ pseudoviewer/
RUN dpkg -i pseudoviewer/ipython.deb && rm pseudoviewer/ipython.deb

# bpnet copy
ADD app/bpnet/bpnet-master.tar.gz /
ADD app/bpnet/001-change-chain-separatator.patch /
RUN cd /bpnet-master \
 && patch -p0 < /001-change-chain-separatator.patch \
 && cd src \
 && make \
 && cp bpnet.linux ../bin/
ADD app/bpnet/metbp-MetBPv1.2.4.tar.gz /
RUN cd /metbp-MetBPv1.2.4 && make

# MC-Annotate copy
ADD app/mc-annotate/mc-annotate.tar.gz /mc-annotate/

# svgcleaner copy
ADD app/svg-cleaner/svgcleaner.tar.gz /svg-cleaner/

# FR3D
ADD app/fr3d/pdbx.tar.gz /py27_env/lib/python2.7/site-packages/
RUN git clone https://github.com/BGSU-RNA/fr3d-python \
 && cd fr3d-python \
 && git checkout ${fr3d_commit} \
 && sed -i '1 i from __future__ import print_function' fr3d/classifiers/NA_pairwise_interactions.py \
 && touch fr3d/modified/__init__.py \
 && /py27_env/bin/pip install .

EXPOSE 80

COPY docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]

COPY src/adapters /rnapdbee-adapters/src/adapters
