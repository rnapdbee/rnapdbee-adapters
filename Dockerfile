FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONPATH=/rnapdbee-adapters/src

RUN apt-get update -y \
 && apt-get install -y \
       build-essential \
       ca-certificates \
       curl \
       ghostscript \
       git \
       gnupg \
       inkscape \
       liblapacke \
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
ADD https://www.tbi.univie.ac.at/RNA/download/ubuntu/ubuntu_24_04/viennarna_2.7.0-1_amd64.deb /tmp/viennarna.deb
RUN dpkg -i /tmp/viennarna.deb

# Install HiGHS
ADD https://github.com/JuliaBinaryWrappers/HiGHSstatic_jll.jl/releases/download/HiGHSstatic-v1.11.0%2B1/HiGHSstatic.v1.11.0.x86_64-linux-gnu-cxx11.tar.gz /usr/local

# Install svgcleaner
ADD https://github.com/RazrFalcon/svgcleaner/releases/download/v0.9.5/svgcleaner_linux_x86_64_0.9.5.tar.gz /usr/local/bin

# Install IronPython
ADD https://github.com/IronLanguages/ironpython3/releases/download/v3.4.2/ironpython_3.4.2.deb /tmp/ironpython.deb
RUN dpkg -i /tmp/ironpython.deb

# PseudoViewer copy
COPY app/pseudoviewer/ pseudoviewer/

EXPOSE 80

COPY docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]

COPY requirements.txt /tmp/requirements.txt
RUN pip install --break-system-packages --ignore-installed -r /tmp/requirements.txt

COPY src/adapters /rnapdbee-adapters/src/adapters
