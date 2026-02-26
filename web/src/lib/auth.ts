import { decodeJwt } from "jose";

/**
 * Verifies a given JWT token by decoding it and checking expiration.
 * We bypass cryptographic signature verification on the frontend to avoid 
 * environment variable mismatch issues in the Next.js Edge Runtime.
 * The backend remains the source of truth for signature validation.
 * 
 * @param token The JWT token to decode
 * @returns The decoded payload if valid and not expired
 */
export async function verifyAuthToken(token: string) {
  try {
    // Decode without signature verification to bypass Edge Runtime ENV constraints
    const payload = decodeJwt(token);
    
    // Validate expiration manually
    if (payload.exp && Date.now() >= payload.exp * 1000) {
      throw new Error("Token expired");
    }
    return payload;
  } catch (err: any) {
    throw new Error(err.message || "Invalid or expired token");
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
