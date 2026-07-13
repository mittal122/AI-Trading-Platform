FROM node:22-alpine AS build

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ .
RUN npm run build

# Unprivileged nginx — runs as a non-root user (uid 101) and listens on
# 8080 instead of 80, so the container needs no root and no cap_net_bind.
FROM nginxinc/nginx-unprivileged:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
# Rewrites the /api upstream to the namespace-qualified service FQDN when
# running under Kubernetes (nginx's resolver ignores resolv.conf search
# domains, so the bare "backend" name only works under Docker DNS).
COPY --chmod=755 docker/40-k8s-upstream.sh /docker-entrypoint.d/40-k8s-upstream.sh

EXPOSE 8080
