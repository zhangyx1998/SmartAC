import express from "express";
import os from "os";
import fs from "fs";
import path from "path";
import { program } from "commander";

// Parse command line arguments
program
  .option(
    "--detections-timeout <seconds>",
    "Timeout in seconds to clear detections after inactivity",
    "10",
  )
  .parse();

const options = program.opts();
const detectionsTimeout = parseFloat(options.detectionsTimeout) * 1000; // Convert to milliseconds

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
let domains: Record<string, number> = {};

// Status for each domain
type Status = {
  population: number;
  fan_power?: number;
  temperature?: number;
  humidity?: number;
  fan_rpm?: number;
};

const status: Map<string, Status> = new Map();

// Timeout handle for clearing detections
let detectionsTimeoutHandle: NodeJS.Timeout | null = null;

function resetDetectionsTimeout() {
  // Clear existing timeout
  if (detectionsTimeoutHandle) {
    clearTimeout(detectionsTimeoutHandle);
  }

  // Set new timeout to clear detections
  detectionsTimeoutHandle = setTimeout(() => {
    domains = {};
    status.clear();
    console.log("Detections cleared due to timeout");
    detectionsTimeoutHandle = null;
  }, detectionsTimeout);
}

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
    domains = detections;

    // Remove status entries for domains not in detections
    const domainNames = new Set(Object.keys(domains));
    for (const domain of status.keys()) {
      if (!domainNames.has(domain)) {
        status.delete(domain);
      }
    }

    resetDetectionsTimeout(); // Reset timeout on new detections
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
  const timestamp = Date.now(); // Unix timestamp in milliseconds
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
    const population = domains[domain] ?? NaN;
    const responseBuffer = Buffer.allocUnsafe(4);
    const power = populationToFanPower(population);
    responseBuffer.writeFloatLE(power, 0);
    res.type("application/octet-stream").send(responseBuffer);

    // Update status for this domain
    status.set(domain, {
      population,
      fan_power: power,
      temperature,
      humidity,
      fan_rpm,
    });

    // Log received data
    console.log(
      `Domain ${domain}`,
      `| Population: ${population}`,
      `| Power: ${power.toFixed(2)}`,
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
      timestamp.toString(),
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

app.get("/status", (req, res) => {
  // Convert Map to Record for JSON response
  const statusRecord: Record<string, Status> = {};

  // Include all domains from detections
  for (const domain of Object.keys(domains)) {
    if (status.has(domain)) {
      // Use existing status if available
      statusRecord[domain] = status.get(domain)!;
    } else {
      // Fill with NaN for unknown fields
      const population = domains[domain];
      statusRecord[domain] = {
        population,
      };
    }
  }

  res.json(statusRecord);
});

app.get("/history/:domain", (req, res) => {
  const domain = req.params.domain;
  const startParam = req.query.start as string | undefined;
  const endParam = req.query.end as string | undefined;
  const stepParam = req.query.step as string | undefined;

  // Parse query parameters
  const start = startParam ? parseFloat(startParam) : undefined;
  const end = endParam ? parseFloat(endParam) : Date.now() / 1000;
  const step = stepParam ? parseFloat(stepParam) : 60; // Default 60 seconds

  // Validate parameters
  if (start !== undefined && isNaN(start)) {
    res.status(400).send("Bad Request: invalid start timestamp");
    return;
  }
  if (isNaN(end)) {
    res.status(400).send("Bad Request: invalid end timestamp");
    return;
  }
  if (isNaN(step) || step <= 0) {
    res.status(400).send("Bad Request: invalid step (must be > 0)");
    return;
  }

  // Read log file for the domain
  const logFile = path.resolve(
    VAR,
    `domain-${normalizeFilenameComponent(domain)}.log`,
  );

  if (!fs.existsSync(logFile)) {
    res.json([]);
    return;
  }

  try {
    // Stream and filter log file line by line
    const fileContent = fs.readFileSync(logFile, "utf-8");
    const lines = fileContent.trim().split("\n");

    const result: string[] = [];
    let lastTime = -Infinity;
    let firstMatchingLine: string | null = null;
    let lastMatchingLine: string | null = null;

    for (const line of lines) {
      if (!line) continue;

      try {
        const parts = line.split(",");
        if (parts.length >= 2) {
          const timestamp = parseFloat(parts[0]); // Parse as numeric timestamp
          const time = timestamp / 1000; // Convert milliseconds to seconds

          // Check if line is within time range
          if (start !== undefined && time < start) continue;
          if (time > end) continue;

          // Track first matching line
          if (firstMatchingLine === null) {
            firstMatchingLine = line;
          }

          // Track last matching line
          lastMatchingLine = line;

          // Check if we should include this line based on step interval
          if (time - lastTime >= step) {
            result.push(line);
            lastTime = time;
          }
        }
      } catch (e) {
        // Skip malformed lines
        continue;
      }
    }

    // Ensure first and last matching lines are always included
    const finalResult: string[] = [];

    if (firstMatchingLine !== null) {
      finalResult.push(firstMatchingLine);
    }

    for (const line of result) {
      if (line !== firstMatchingLine && line !== lastMatchingLine) {
        finalResult.push(line);
      }
    }

    if (lastMatchingLine !== null && lastMatchingLine !== firstMatchingLine) {
      finalResult.push(lastMatchingLine);
    }

    res.type("text/plain").send(finalResult.join("\n"));
  } catch (error) {
    console.error(`Error reading history for domain ${domain}:`, error);
    res.status(500).send("Internal Server Error");
  }
});

// Catch-all route - serve static folder
app.use(express.static(STATIC));

app.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
  console.log(`Detections timeout: ${detectionsTimeout / 1000}s`);
  const ips = getLocalIPs();
  if (ips.length > 0) {
    ips.forEach((ip) => {
      console.log(`http://${ip}:${PORT}`);
    });
  } else {
    console.log(`http://localhost:${PORT}`);
  }
});
