// neon.ts - what this folder provisions on the ehpa-database project (steep-rain-79347575): Neon Auth (Managed Better Auth,
// William's sign-in) and ONE Neon Function, slug `ehpadb`, that serves the practice database app. Applied with `neon deploy`
// from this folder (the folder is linked to the project with `neon link`; the .neon and .env files it writes are git-ignored).
// Two gates on the data: the signed-in account's email must be on ALLOWED_EMAILS, and its owner must have confirmed that address
// (Google sign-in arrives confirmed; a password sign-up does not until email confirmation is turned on). Anything else gets 403.
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
