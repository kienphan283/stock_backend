import path from "path";
import dotenv from "dotenv";

const rootEnvPath = path.resolve(__dirname, "../../..", ".env");
dotenv.config({ path: rootEnvPath });

