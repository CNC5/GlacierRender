FROM python
RUN apt update
RUN apt install -y blender
RUN useradd -ms /bin/bash render_agent
USER render_agent
WORKDIR /home/render_agent
RUN pip install tornado sqlalchemy psycopg2 nvidia-ml-py
RUN curl -o /home/render_agent/blender.tar.xz https://mirrors.dotsrc.org/blender/release/Blender3.5/blender-3.5.1-linux-x64.tar.xz
RUN tar -xpvf blender.tar.xz && rm blender.tar.xz
ENV BLENDER_BIN=/home/render_agent/blender-3.5.1-linux-x64/blender
COPY server.py .
COPY authenticator.py .
COPY database.py .
COPY render.py .
ENTRYPOINT python -i server.py
