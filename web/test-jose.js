import { jwtVerify } from 'jose';
import fs from 'fs';

const secret = new TextEncoder().encode("super-secret-default-key-1234");
const token = fs.readFileSync('../test_token.txt', 'utf8').trim();

async function run() {
  try {
    const verified = await jwtVerify(token, secret);
    console.log("Verified:", verified.payload);
  } catch (e) {
    console.error("Error:", e);
  }
}
run();
