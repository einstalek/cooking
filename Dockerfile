FROM python:3
WORKDIR /Users/einstalek/graph_docker
ENV PYTHONPATH "${PYTHONPATH}:/Users/einstalek/graph"
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "servers/hardware_emulator.py"]
