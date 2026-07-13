# Official postgres:17-alpine, hardened for image-scan + Kubernetes gates:
#
# 1. The bundled `gosu` binary is a Go executable compiled against an
#    outdated Go stdlib and permanently trips trivy CRITICAL gates
#    (e.g. CVE-2025-68121); upstream rebuilds lag Go patch releases.
#    Postgres itself and all alpine packages scan clean. gosu's only job is
#    the root→postgres step-down in the entrypoint — alpine's `su-exec`
#    (a ~14KB C utility, same CLI) does it identically, so gosu is deleted
#    and the entrypoint's single call is patched. NOTE: do NOT leave a
#    symlink named "gosu" pointing at su-exec — trivy attributes the target
#    to the "gosu" path and keeps flagging it (verified empirically).
#
# 2. USER 70 (postgres uid in alpine, numeric): Kubernetes runAsNonRoot can
#    only verify numeric UIDs, and the stock image starts as root. The
#    entrypoint fully supports starting as the postgres user directly —
#    the su-exec path only matters if someone runs it as root explicitly.
FROM postgres:17-alpine

RUN apk add --no-cache su-exec \
    && rm /usr/local/bin/gosu \
    && sed -i 's/exec gosu postgres/exec su-exec postgres/' /usr/local/bin/docker-entrypoint.sh

USER 70
