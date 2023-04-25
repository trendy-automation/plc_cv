# pull base image
FROM alpine:3.17

ENV ANSIBLE_CORE 7.4.0
ENV TZ Europe/Moscow

RUN CARGO_NET_GIT_FETCH_WITH_CLI=1 && \
    apk --no-cache add \
        sudo \
        python3\
        py3-pip \
        openssl \
        ca-certificates \
        sshpass \
        openssh-client \
        rsync \
        git && \
    apk --no-cache add --virtual build-dependencies \
        python3-dev \
        libffi-dev \
        musl-dev \
        gcc \
        cargo \
        build-base && \
    pip install --upgrade pip wheel && \
    pip install --upgrade cryptography cffi && \
    pip install ansible==${ANSIBLE_CORE} && \
    pip install --upgrade pywinrm && \
    apk del build-dependencies && \
    rm -rf /var/cache/apk/* && \
    rm -rf /root/.cache/pip && \
    rm -rf /root/.cargo

RUN mkdir /ansible && \
    mkdir -p /etc/ansible && \
    echo "[ubuntu-cv]" > /etc/ansible/hosts && \
    echo "192.168.0.12 ansible_user=root ansible_ssh_pass=3470 ansible_ssh_extra_args='-o StrictHostKeyChecking=no'" >> /etc/ansible/hosts
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /ansible/playbooks

ENTRYPOINT ["ansible-playbook"]
