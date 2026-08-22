/**
 * Hybrid slug utilities: "real-madrid-vs-man-city-984512"
 *
 * Format: {human-readable-slug}-{numeric_id}
 *
 * - The slug part boosts SEO (Google reads "real-madrid-vs-man-city")
 * - The numeric ID at the end enables O(1) database lookups
 * - If the slug is wrong, we still extract the ID and redirect to the canonical URL
 */

const SLUG_ID_SEPARATOR = "-";

/**
 * Build a hybrid slug from a name and numeric ID.
 * Example: buildSlug("Real Madrid vs Man City", 984512)
 *       => "real-madrid-vs-man-city-984512"
 */
export function buildSlug(name: string, id: number): string {
  const slugPart = name
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, "") // strip non-alphanumeric (except spaces/hyphens)
    .replace(/\s+/g, "-")          // spaces → hyphens
    .replace(/-+/g, "-")           // collapse multiple hyphens
    .replace(/^-|-$/g, "");        // trim leading/trailing hyphens
  return `${slugPart}${SLUG_ID_SEPARATOR}${id}`;
}

/**
 * Extract the numeric ID from the tail of a hybrid slug.
 * Returns null if no numeric tail is found.
 *
 * Example: extractId("real-madrid-vs-man-city-984512") => 984512
 */
export function extractId(slug: string): number | null {
  const match = slug.match(/(\d+)$/);
  return match ? parseInt(match[1], 10) : null;
}

/**
 * Extract the human-readable slug part (everything before the numeric ID).
 * Useful for display or canonical URL comparison.
 *
 * Example: extractSlugPart("real-madrid-vs-man-city-984512")
 *       => "real-madrid-vs-man-city"
 */
export function extractSlugPart(slug: string): string {
  return slug.replace(/-\d+$/, "");
}

/**
 * Validate whether a full slug matches the expected canonical form.
 * Useful for SSR redirect logic: if someone visits with a stale slug
 * but correct ID, redirect to the canonical URL.
 */
export function isCanonicalSlug(
  fullSlug: string,
  canonicalName: string,
  id: number
): boolean {
  return fullSlug === buildSlug(canonicalName, id);
}
