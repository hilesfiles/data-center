# Application release 1.54 — map marker legibility

Application release 1.54 keeps all 18 completed project audits on the community map while correcting a national-zoom overlap between Apple Washoe County and Switch Citadel / Tahoe Reno 1. Nearby projects receive small, presentation-only horizontal marker lanes; their stored geographic coordinates remain unchanged, and each marker retains its own project link.

The national-view circle diameter is reduced from roughly 19 pixels to roughly 11 pixels. County and project popup wording now identifies completed research rather than incorrectly describing every mapped location as a full modeled county account.

The TypeScript check, production build, and complete browser suite pass. Browser regression coverage confirms that both Reno-area markers are independently reachable, all 18 completed audits remain mapped, and the direct county-detail link remains available.
