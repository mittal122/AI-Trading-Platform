#!/bin/sh
# Kubernetes DNS fix for the /api proxy.
#
# nginx's `resolver` directive does NOT use /etc/resolv.conf search domains,
# so the bare upstream name "backend" resolves under Docker (its DNS answers
# container names directly) but never under Kubernetes, where CoreDNS only
# answers the namespace-qualified FQDN. At startup, if resolv.conf shows a
# Kubernetes search path, rewrite the proxy target to
# backend.<namespace>.svc.cluster.local and point the resolver at the
# cluster's actual DNS server.
#
# Must never exit non-zero (the nginx entrypoint aborts on failing scripts):
# on a read-only filesystem this logs and leaves the Docker defaults.
conf=/etc/nginx/conf.d/default.conf
domain=$(awk '/^search/ {print $2; exit}' /etc/resolv.conf 2>/dev/null)
dns_ip=$(awk '/^nameserver/ {print $2; exit}' /etc/resolv.conf 2>/dev/null)

case "$domain" in
  *.svc.cluster.local)
    if sed -i \
        -e "s|http://backend:8000|http://backend.${domain}:8000|" \
        -e "s|resolver [^;]*;|resolver ${dns_ip} valid=10s ipv6=off;|" \
        "$conf" 2>/dev/null; then
      echo "40-k8s-upstream: /api upstream -> backend.${domain}:8000 (resolver ${dns_ip})"
    else
      echo "40-k8s-upstream: $conf not writable; keeping defaults (route /api via ingress instead)"
    fi
    ;;
esac
exit 0
