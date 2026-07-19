/**
 * Resolve tenant slug from browser hostname for subdomain routing.
 * Example: clinic1.emr.localhost → "clinic1"
 */

const RESERVED = new Set(['www', 'api', 'app', 'admin', 'mail', 'static', 'cdn']);

export function getTenantSlugFromHostname(
  hostname: string = window.location.hostname,
  baseDomain: string = import.meta.env.VITE_TENANT_BASE_DOMAIN || 'localhost'
): string | null {
  const host = hostname.toLowerCase().split(':')[0];
  const base = baseDomain.toLowerCase();

  if (host === base) {
    return null;
  }

  const suffix = `.${base}`;
  if (!host.endsWith(suffix)) {
    return null;
  }

  const subdomain = host.slice(0, -suffix.length);
  if (!subdomain || subdomain.includes('.') || RESERVED.has(subdomain)) {
    return null;
  }

  return subdomain;
}

export function isSubdomainTenantEnabled(): boolean {
  return import.meta.env.VITE_TENANT_SUBDOMAIN_ENABLED === 'true';
}
