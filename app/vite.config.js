import { statSync } from "node:fs";
import { defineConfig } from "vite";

const brandingLimits = { "logo.png": 50_000, "cover.jpg": 300_000 };

const brandingSizeCheck = {
  name: "branding-size-check",
  apply: "build",
  buildStart() {
    for (const [file, maxBytes] of Object.entries(brandingLimits)) {
      const path = new URL(`./src/branding/${file}`, import.meta.url);
      const image = statSync(path, { throwIfNoEntry: false });
      if (image && image.size > maxBytes) {
        this.error(`src/branding/${file} is ${image.size} bytes. Limit: ${maxBytes} bytes.`);
      }
    }
  },
};

// Relative base: the same build works at a domain root (Render, S3) or under a sub-path.
export default defineConfig({
  base: "./",
  plugins: [brandingSizeCheck],
});
