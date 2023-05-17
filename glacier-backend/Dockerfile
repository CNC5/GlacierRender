FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04
RUN apt update
RUN apt install -y curl xz-utils
RUN useradd -ms /bin/bash render_agent
WORKDIR /home/render_agent
RUN curl -o /home/render_agent/blender.tar.xz https://mirrors.dotsrc.org/blender/release/Blender3.5/blender-3.5.1-linux-x64.tar.xz
RUN tar -xpvf blender.tar.xz && rm blender.tar.xz
ENV BLENDER_BIN=/home/render_agent/blender-3.5.1-linux-x64/blender
RUN apt install -y blender python3 python3-pip libsm6 libcudart11.0
RUN pip install tornado sqlalchemy psycopg2-binary nvidia-ml-py argon2-cffi
USER render_agent
ADD . /home/render_agent/GlacierRender/glacier-backend/
WORKDIR /home/render_agent/GlacierRender/glacier-backend
ENTRYPOINT python3 server.py