import express from "express";
import { createHash, timingSafeEqual } from "node:crypto";

// Keep the public flow name callable without loading or constructing paid SDKs.
export async function actionGlassSeoFlow(_input: { service: string; location?: string }) {
  throw new Error("SERVICE_HELD: SEO generation is held pending an approved local inference implementation and distinct service topology");
}

export function localAdmin(req: express.Request, res: express.Response, next: express.NextFunction) {
  res.set("Cache-Control", "private, no-store");
  const token = process.env.AI_BS_LOCAL_ADMIN_TOKEN;
  if (!token || !token.trim()) {
    return res.status(503).json({ error: "Local administrator access is not configured", code: "ADMIN_UNCONFIGURED" });
  }
  const authorization = req.headers.authorization;
  const supplied = typeof authorization === "string" ? authorization : "";
  const digest = (value: string) => createHash("sha256").update(value).digest();
  if (!timingSafeEqual(digest(supplied), digest(`Bearer ${token}`))) {
    return res.status(401).json({ error: "Administrator authentication required" });
  }
  next();
}

export function createApp() {
  const app = express();
  app.use(localAdmin);
  app.post("/api/actionGlassSeoFlow", (_req, res) => {
    res.set("Cache-Control", "private, no-store");
    return res.status(503).json({ code: "SERVICE_HELD", error: "SEO generation is held pending an approved local inference implementation and distinct service topology" });
  });
  return app;
}

// Deliberately no listener: port 3001 belongs to the independent Node service.
// A distinct approved topology and local inference implementation are required.
