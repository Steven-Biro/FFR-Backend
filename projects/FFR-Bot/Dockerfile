FROM gorialis/discord.py:3.8-alpine-pypi-minimal
WORKDIR /usr/src/app
COPY requirments.txt .

RUN python -m pip install -r requirments.txt

COPY src ./
COPY token.txt .

CMD ["python", "./main.py"]

