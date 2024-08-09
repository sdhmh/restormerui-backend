FROM ubuntu:jammy


RUN apt-get update && \
    apt-get install -y wget libgl1-mesa-glx libgl1-mesa-dri libgl1-mesa-dev libglib2.0-0 && \
    apt-get clean && \
    rm -rf /var/cache/debconf/* \
    /var/lib/apt/lists/* \
    /var/log/* \
    /var/tmp/* \
    /tmp/* \
    /usr/share/doc/* \
    /usr/share/man/* \
    /usr/share/local/*

# Create a separate non-root user
RUN useradd -m -s /bin/bash app

USER app
WORKDIR /setup

RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh && \
    bash /setup/Miniconda3-latest-Linux-x86_64.sh -b -p /setup/miniconda3 && \
    rm -rf Miniconda3-latest-Linux-x86_64.sh

# Install pytorch using miniconda
RUN . /setup/miniconda3/bin/activate && \
    conda create -n app python=3.7 -y && \
    conda activate app && \
    conda install pytorch=1.8 torchvision torchaudio cpuonly -c pytorch -y
COPY requirements.txt .
# Install dependencies using pip
RUN . /setup/miniconda3/bin/activate && conda activate app && pip install -r requirements.txt

WORKDIR /app

COPY . .

EXPOSE 8000

ENV ENVIORNMENT=PRODUCTION

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 CMD [ "/bin/bash", "-c", "echo > /dev/tcp/127.0.0.1/8000" ]

CMD [ "/bin/bash", "-c", ". /setup/miniconda3/bin/activate && conda activate app && uvicorn main:app --host 0.0.0.0" ]
