// Runtime API configuration — loaded before the app bundle, NOT compiled in.
// Empty string = same-origin relative calls ("/api/..."), which is correct for
// every proxied deployment (Vite dev, Docker nginx, Kubernetes ingress, Vercel
// rewrites). A deployment can override WITHOUT rebuilding by replacing this
// one file (e.g. a Kubernetes ConfigMap mounted at
// /usr/share/nginx/html/config.js) with:
//   window.__API_BASE__ = 'https://api.example.com'
window.__API_BASE__ = '';
