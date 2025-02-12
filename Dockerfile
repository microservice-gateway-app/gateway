ARG PYTHON_BASE=3.12-alpine
# Base Image (with base APT packages)
FROM python:$PYTHON_BASE AS base

# build stage
FROM base AS builder

# install PDM
RUN pip install -U pdm
# disable update check
ENV PDM_CHECK_UPDATE=false
# copy files
COPY pyproject.toml README.md /project/

# install dependencies and project into the local packages directory
WORKDIR /project
RUN pdm install --prod --no-editable --no-self --no-isolation
COPY src/ /project/src

# run stage
FROM base

# retrieve packages from build stage
COPY --from=builder /project/.venv/ /project/.venv
ENV PATH="/project/.venv/bin:$PATH"
ENV PYTHONPATH="/project/src"
# set command/entrypoint, adapt to fit your needs
COPY src /project/src
COPY .env services.compose.json /project/
COPY ./keys/ /project/keys
WORKDIR /project
CMD [ "uvicorn", "main:app", "--host", "0.0.0.0" ]
