const { jwtVerify } = require('jose');
const jwt = require('jsonwebtoken');

const secret = new TextEncoder().encode("super-secret-default-key-1234");
const token = jwt.sign({ sub: 'test', exp: Math.floor(Date.now() / 1000) + 3600 }, "super-secret-default-key-1234", { algorithm: 'HS256' });

async function run() {
  try {
    const verified = await jwtVerify(token, secret);
    console.log("Verified:", verified.payload);
  } catch (e) {
    console.error("Error:", e);
  }
}
run();
