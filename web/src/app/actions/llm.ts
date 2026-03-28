"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { clearSession } from "@/app/actions/auth";
import { buildBearerHeaders, getServerAccessToken } from "@/lib/server-auth";

const API_URL = process.env.API_URL || "http://127.0.0.1:8000/api";

export interface LLMConfigSectionInput {
  base_url: string;
  api_key: string;
  model: string;
}

export interface LLMConfigInput {
  main: LLMConfigSectionInput;
  skill_generation: LLMConfigSectionInput;
}

export async function updateLLMConfig(payload: LLMConfigInput) {
  const token = await getServerAccessToken();
  if (!token) {
    await clearSession();
    redirect("/login");
  }

  try {
    const response = await fetch(`${API_URL}/admin/llm-config`, {
      method: "POST",
      headers: buildBearerHeaders(token, { "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      if (response.status === 401) {
        await clearSession();
        redirect("/login");
      }
      const data = await response.json();
      return { error: data.detail || "Failed to update LLM config" };
    }

    const result = await response.json();
    revalidatePath("/llm");
    return { data: result };
  } catch (error) {
    console.error("Update LLM config error:", error);
    return { error: "Failed to connect to backend" };
  }
}
