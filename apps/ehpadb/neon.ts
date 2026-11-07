// neon.ts - what this folder provisions on the ehpa-database project (steep-rain-79347575): Neon Auth (Managed Better Auth,
// William's sign-in) and ONE Neon Function, slug `ehpadb`, that serves the practice database app. Applied with `neon deploy`
// from this folder (the folder is linked to the project with `neon link`; the .neon and .env files it writes are git-ignored).
// ALLOWED_EMAILS is the only gate on the data: a signed-in account whose email is not listed gets 403 from every /api route.
import { defineConfig } from "@neon/config/v1";

export default defineConfig({
  auth: true,
  functions: {
    ehpadb: {
      name: "ehpa Practice Database",
      source: "src/index.ts",
      env: {
        ALLOWED_EMAILS: "dreffinger@gmail.com",
        SESSION_IDLE_MINUTES: "30",
      },
    },
  },
});
