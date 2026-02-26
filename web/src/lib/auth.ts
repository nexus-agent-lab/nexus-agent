import { jwtVerify } from "jose";

/**
 * Returns the JWT secret key encoded for use with the `jose` library.
 * It matches the backend's default secret if no environment variable is provided.
 */
export function getJwtSecretKey(): Uint8Array {
  const secret = process.env.JWT_SECRET || "super-secret-default-key-1234";
  if (!process.env.JWT_SECRET) {
    console.warn("JWT_SECRET is not set, using default key.");
  }
  return new TextEncoder().encode(secret);
}
  const secret = process.env.JWT_SECRET || "super-secret-default-key-1234";
  return new TextEncoder().encode(secret);
}

/**
 * Verifies a given JWT token.
 * 
 * @param token The JWT token to verify
 * @returns The decoded payload if valid, otherwise throws an error
 */
export async function verifyAuthToken(token: string) {
  try {
    const verified = await jwtVerify(token, getJwtSecretKey());
    return verified.payload;
  } catch {
    throw new Error("Invalid or expired token");
  }
}


/**
 * Represents the user data stored in the JWT payload.
 */
export interface UserPayload {
  sub: string;
  username: string;
  role: string;
  api_key: string;
  exp: number;
}
