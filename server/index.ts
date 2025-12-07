import express from "express";
import os from "os";
import fs from "fs";
import path from "path";

const app = express();
const PORT = 3000;

function populationToFanPower(population: number) {
  // Preserve NaN
  if (isNaN(population)) return NaN;
  // Simple linear mapping: 0 people -> 0.0 power, 100 people -> 1.0 power
  const maxPopulation = 2;
  const clampedPopulation = Math.min(Math.max(population, 0), maxPopulation);
  return clampedPopulation / maxPopulation;
}

function getLocalIPs() {
  const interfaces = os.networkInterfaces();
  const ips = [];
  for (const iface of Object.values(interfaces)) {
    if (!iface) continue;
    for (const node of iface) {
      // Skip internal and non-IPv4 addresses
      if (!node.internal && node.family === "IPv4") {
        ips.push(node.address);
      }
    }
  }
  return ips;
}

function ensureDir(folderPath: string) {
  if (!fs.existsSync(folderPath)) {
    fs.mkdirSync(folderPath, { recursive: true });
  }
}

function normalizeFilenameComponent(name: string) {
  return name.replace(/[^a-z0-9_\-]/gi, "_");
}

const VAR = path.resolve("var");
ensureDir(VAR);

const STATIC = path.resolve("static");

// Record of current population density per domain
const domains = new Map<string, number>();

// Parse binary data
app.use(express.raw({ type: "application/octet-stream", limit: "10mb" }));

// Parse JSON
app.use(express.json());

app.post("/detections", (req, res) => {
  // Only accept JSON
  if (req.is("application/json")) {
    const detections = req.body;
    if (typeof detections !== "object" || detections === null) {
      res.status(400).send("Bad Request: body must be a JSON object.");
      return;
    }
    for (const [domain, count] of Object.entries(detections)) {
      if (typeof count === "number" && count >= 0) {
        domains.set(domain, count);
        console.log(`Domain ${domain} population updated to ${count}`);
      } else {
        console.log(
          `Invalid count for domain ${domain}: ${count}, must be a non-negative number.`,
        );
      }
    }
    res.status(200).end();
  } else {
    res
      .status(400)
      .send(
        `Bad Request type ${req.headers["content-type"]}, expected application/json.`,
      );
  }
});

app.post("/unit/:domain", (req, res) => {
  const timestamp = new Date().toISOString();
  // Extract domain name from URL
  const domain = req.params.domain || "default";
  // Log body based on content type
  const contentType = req.headers["content-type"] || "";
  if (
    contentType.includes("application/octet-stream") &&
    Buffer.isBuffer(req.body) &&
    req.body.length >= 12
  ) {
    // Parse as floats for SmartAC telemetry
    const temperature = req.body.readFloatLE(0);
    const humidity = req.body.readFloatLE(4);
    const fan_rpm = req.body.readFloatLE(8);
    // Send response with fan power as binary float
    const population = domains.get(domain) ?? NaN;
    const responseBuffer = Buffer.allocUnsafe(4);
    responseBuffer.writeFloatLE(populationToFanPower(population), 0);
    res.type("application/octet-stream").send(responseBuffer);
    // Log received data
    console.log(
      `Domain ${domain}`,
      `| Population: ${population}`,
      `| Temperature: ${temperature.toFixed(2)}°C`,
      `| Humidity: ${humidity.toFixed(2)}%`,
      `| Fan RPM: ${fan_rpm.toFixed(2)}`,
    );
    // Append record to log file (optional)
    const db = path.resolve(
      VAR,
      `domain-${normalizeFilenameComponent(domain)}.log`,
    );
    const line = [
      JSON.stringify(timestamp),
      JSON.stringify({ temperature, humidity, fan_rpm, population }),
    ].join(",");
    fs.appendFile(db, line + "\n", (err) => {
      if (err) {
        console.error(`Failed to write to log file ${db}:`, err);
      }
    });
  } else {
    // Bad request
    console.log("Body:", req.body);
    res.status(400).send("Bad Request");
  }
});

// Catch-all route - serve static folder
app.use(express.static(STATIC));

app.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
  const ips = getLocalIPs();
  if (ips.length > 0) {
    ips.forEach((ip) => {
      console.log(`http://${ip}:${PORT}`);
    });
  } else {
    console.log(`http://localhost:${PORT}`);
  }
});
