FROM almalinux:8

# Maintainer
MAINTAINER Nathan J. Edwards <nje5@georgetown.edu>


ENV CONNECT="https://d3gcli72yxqn2z.cloudfront.net/downloads/connect/latest/bin/ibm-aspera-connect_4.2.13.820_linux_x86_64.tar.gz"

USER root

RUN \
  set -x && \   
  dnf -y update && \
  mkdir -p /data && \
  chmod a+t,a+rwX /data && \
  useradd -ms /bin/bash ascp

USER ascp

RUN \
  cd /home/ascp && \
  curl "$CONNECT" | tar xvz -f - && \
  /bin/bash ibm-aspera-connect_*.sh > /dev/null 2>&1 && \
  rm -f ibm-aspera-connect_*.sh && \
  chmod a+rX /home/ascp

WORKDIR /data

ENTRYPOINT ["/home/ascp/.aspera/connect/bin/ascp"]

