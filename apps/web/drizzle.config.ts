import { defineConfig } from "drizzle-kit"

export default defineConfig({
  schema: "./db/schema.ts",
  out: "./db/migrations",
  dialect: "postgresql",
  dbCredentials: {
    url:
      process.env.DATABASE_URL?.replace(
        "postgresql+asyncpg://",
        "postgresql://",
      ) ?? "postgresql://postgres:dev_password@localhost:5432/eco_dashboard",
  },
})
