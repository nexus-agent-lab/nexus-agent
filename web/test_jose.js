const { jwtVerify } = require("jose");

const token = require("fs").readFileSync("token.txt", "utf-8").trim();

async function run() {
  const secret = process.env.JWT_SECRET || "super-secret-default-key-1234";
  const key = new TextEncoder().encode(secret);
  try {
    const verified = await jwtVerify(token, key);
    console.log("Verified:", verified.payload);
  } catch (err) {
    console.error("Error:", err.message);
  }
}
run();
